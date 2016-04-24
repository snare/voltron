from __future__ import print_function

import logging
import threading
import re
import struct
import six

from voltron.api import *
from voltron.plugin import *
from voltron.dbg import *

try:
    import gdb
    HAVE_GDB = True
except ImportError:
    HAVE_GDB = False

log = logging.getLogger('debugger')

if HAVE_GDB:

    class GDBAdaptor(DebuggerAdaptor):
        archs = {
            'i386': 'x86', 'i386:intel': 'x86', 'i386:x64-32': 'x86', 'i386:x64-32:intel': 'x86', 'i8086': 'x86',
            'i386:x86-64': 'x86_64', 'i386:x86-64:intel': 'x86_64',
            'arm': 'arm', 'armv2': 'arm', 'armv2a': 'arm', 'armv3': 'arm', 'armv3m': 'arm', 'armv4': 'arm',
            'armv4t': 'arm', 'armv5': 'arm', 'armv5t': 'arm', 'armv5te': 'arm',
            'powerpc:common': 'powerpc'
        }
        sizes = {
            'x86': 4,
            'x86_64': 8,
            'arm': 4,
            'powerpc': 4,
        }
        max_frame = 64
        max_string = 128

        """
        The interface with an instance of GDB
        """
        def __init__(self, *args, **kwargs):
            self.listeners = []
            self.host_lock = threading.RLock()
            self.host = gdb

        def version(self):
            """
            Get the debugger's version.

            Returns a string containing the debugger's version
            (e.g. 'GNU gdb (GDB) 7.8')
            """
            output = gdb.execute('show version', to_string=True)
            try:
                version = output.split('\n')[0]
            except:
                version = None
            return version

        def _target(self, target_id=0):
            """
            Return information about the specified target.

            Returns data in the following structure:
            {
                "id":       0,         # ID that can be used in other funcs
                "file":     "/bin/ls", # target's binary file
                "arch":     "x86_64",  # target's architecture
                "state:     "stopped"  # state
            }
            """
            # get target
            target = gdb.selected_inferior()

            # get target properties
            d = {}
            d["id"] = 0
            d["num"] = target.num

            # get target state
            d["state"] = self._state()

            # get inferior file (doesn't seem to be available through the API)
            lines = list(filter(lambda x: x != '', gdb.execute('info inferiors', to_string=True).split('\n')))
            if len(lines) > 1:
                info = list(filter(lambda x: '*' in x[0], map(lambda x: x.split(), lines[1:])))
                d["file"] = info[0][-1]
            else:
                log.debug("No inferiors in `info inferiors`")
                raise NoSuchTargetException()

            # get arch
            d["arch"] = self.get_arch()
            d['byte_order'] = self.get_byte_order()
            d['addr_size'] = self.get_addr_size()

            return d

        @lock_host
        def target(self, target_id=0):
            """
            Return information about the current inferior.

            GDB only supports querying the currently selected inferior, rather
            than an arbitrary target like LLDB, because the API kinda sucks.

            `target_id` is ignored.
            """
            return self._target()

        @lock_host
        def targets(self, target_ids=None):
            """
            Return information about the debugger's current targets.

            `target_ids` is ignored. Only the current target is returned. This
            method is only implemented to maintain API compatibility with the
            LLDBAdaptor.
            """
            return [self._target()]

        @validate_target
        @lock_host
        def state(self, target_id=0):
            """
            Get the state of a given target.
            """
            return self._state()

        @validate_busy
        @validate_target
        @lock_host
        def registers(self, target_id=0, thread_id=None, registers=[]):
            """
            Get the register values for a given target/thread.
            """
            arch = self.get_arch()

            # if we got 'sp' or 'pc' in registers, change it to whatever the right name is for the current arch
            if arch in self.reg_names:
                if 'pc' in registers:
                    registers.remove('pc')
                    registers.append(self.reg_names[arch]['pc'])
                if 'sp' in registers:
                    registers.remove('sp')
                    registers.append(self.reg_names[arch]['sp'])
            else:
                raise Exception("Unsupported architecture: {}".format(target['arch']))

            # get registers
            if registers != []:
                regs = {}
                for reg in registers:
                    regs[reg] = self.get_register(reg)
            else:
                log.debug('Getting registers for arch {}'.format(arch))
                if arch == "x86_64":
                    regs = self.get_registers_x86_64()
                elif arch == "x86":
                    regs = self.get_registers_x86()
                elif arch == "arm":
                    regs = self.get_registers_arm()
                elif arch == "powerpc":
                    regs = self.get_registers_powerpc()
                else:
                    raise UnknownArchitectureException()

            return regs

        @validate_busy
        @validate_target
        @lock_host
        def stack_pointer(self, target_id=0, thread_id=None):
            """
            Get the value of the stack pointer register.
            """
            arch = self.get_arch()
            if arch in self.reg_names:
                sp_name = self.reg_names[arch]['sp']
                sp = self.get_register(sp_name)
            else:
                raise UnknownArchitectureException()

            return sp_name, sp

        @validate_busy
        @validate_target
        @lock_host
        def program_counter(self, target_id=0, thread_id=None):
            """
            Get the value of the program counter register.
            """
            arch = self.get_arch()
            if arch in self.reg_names:
                pc_name = self.reg_names[arch]['pc']
                pc = self.get_register(pc_name)
            else:
                raise UnknownArchitectureException()

            return pc_name, pc

        @validate_busy
        @validate_target
        @lock_host
        def memory(self, address, length, target_id=0):
            """
            Get the register values for .

            `address` is the address at which to start reading
            `length` is the number of bytes to read
            """
            # read memory
            log.debug('Reading 0x{:x} bytes of memory at 0x{:x}'.format(length, address))
            memory = bytes(gdb.selected_inferior().read_memory(address, length))
            return memory

        @validate_busy
        @validate_target
        @lock_host
        def stack(self, length, target_id=0, thread_id=None):
            """
            Get the register values for .

            `length` is the number of bytes to read
            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get the stack pointer
            sp_name, sp = self.stack_pointer(target_id=target_id, thread_id=thread_id)

            # read memory
            memory = self.memory(sp, length, target_id=target_id)

            return memory

        @validate_busy
        @validate_target
        @lock_host
        def disassemble(self, target_id=0, address=None, count=16):
            """
            Get a disassembly of the instructions at the given address.

            `address` is the address at which to disassemble. If None, the
            current program counter is used.
            `count` is the number of instructions to disassemble.
            """
            # make sure we have an address
            if address == None:
                pc_name, address = self.program_counter(target_id=target_id)

            # disassemble
            output = gdb.execute('x/{}i 0x{:x}'.format(count, address), to_string=True)

            return output

        @validate_busy
        @validate_target
        @lock_host
        def dereference(self, pointer, target_id=0):
            """
            Recursively dereference a pointer for display
            """
            fmt = ('<' if self.get_byte_order() == 'little' else '>') + {2: 'H', 4: 'L', 8: 'Q'}[self.get_addr_size()]

            addr = pointer
            chain = []

            # recursively dereference
            while True:
                try:
                    mem = gdb.selected_inferior().read_memory(addr, self.get_addr_size())
                    # log.debug("read mem: {}".format(mem))
                    (ptr,) = struct.unpack(fmt, mem)
                    if ptr in chain:
                        break
                    chain.append(('pointer', addr))
                    addr = ptr
                except gdb.MemoryError:
                    log.exception("Dereferencing pointer 0x{:X}".format(addr))
                    break

            # get some info for the last pointer
            # first try to resolve a symbol context for the address
            if len(chain):
                p, addr = chain[-1]
                output = gdb.execute('info symbol 0x{:x}'.format(addr), to_string=True)
                log.debug('output = {}'.format(output))
                if 'No symbol matches' not in output:
                    chain.append(('symbol', output.strip()))
                    log.debug("symbol context: {}".format(str(chain[-1])))
                else:
                    log.debug("no symbol context, trying as a string")
                    mem = gdb.selected_inferior().read_memory(addr, 2)
                    if ord(mem[0]) <= 127 and ord(mem[0]) != 0:
                        a = []
                        for i in range(0, self.max_string):
                            mem = gdb.selected_inferior().read_memory(addr + i, 1)
                            if ord(mem[0]) == 0 or ord(mem[0]) > 127:
                                break
                            if isinstance(mem, memoryview):
                                a.append(mem.tobytes().decode('latin1'))
                            else:
                                a.append(str(mem))
                        chain.append(('string', ''.join(a)))

            log.debug("chain: {}".format(chain))
            return chain

        @lock_host
        def command(self, command=None):
            """
            Execute a command in the debugger.

            `command` is the command string to execute.
            """
            if command:
                res = gdb.execute(command, to_string=True)
            else:
                raise Exception("No command specified")

            return res

        @lock_host
        def disassembly_flavor(self):
            """
            Return the disassembly flavor setting for the debugger.

            Returns 'intel' or 'att'
            """
            flavor = re.search('flavor is "(.*)"', gdb.execute("show disassembly-flavor", to_string=True)).group(1)
            return flavor

        @lock_host
        def breakpoints(self, target_id=0):
            """
            Return a list of breakpoints.

            Returns data in the following structure:
            [
                {
                    "id":           1,
                    "enabled":      True,
                    "one_shot":     False,
                    "hit_count":    5,
                    "locations": [
                        {
                            "address":  0x100000cf0,
                            "name":     'main'
                        }
                    ]
                }
            ]
            """
            breakpoints = []

            # hahahahaha GDB sucks so much
            for b in gdb.breakpoints():
                try:
                    if b.location.startswith('*'):
                        addr = int(b.location[1:], 16)
                    else:
                        output = gdb.execute('info addr {}'.format(b.location), to_string=True)
                        m = re.match('.*is at ([^ ]*) .*', output)
                        if not m:
                            m = re.match('.*at address ([^ ]*)\..*', output)
                        if m:
                            addr = int(m.group(1), 16)
                        else:
                            addr = 0
                except:
                    addr = 0

                breakpoints.append({
                    'id':           b.number,
                    'enabled':      b.enabled,
                    'one_shot':     b.temporary,
                    'hit_count':    b.hit_count,
                    'locations':    [{
                        "address":  addr,
                        "name":     b.location
                    }]
                })

            return breakpoints

        @lock_host
        def backtrace(self, target_id=0, thread_id=None):
            """
            Return a list of stack frames.
            """
            frames = []
            f = gdb.newest_frame()
            for i in range(self.max_frame):
                if not f:
                    break
                frames.append({'index': i, 'addr': f.pc(), 'name': f.name()})
                f = f.older()

            return frames

        def capabilities(self):
            """
            Return a list of the debugger's capabilities.

            Thus far only the 'async' capability is supported. This indicates
            that the debugger host can be queried from a background thread,
            and that views can use non-blocking API requests without queueing
            requests to be dispatched next time the debugger stops.
            """
            return []

        #
        # Private functions
        #

        def _state(self):
            """
            Get the state of a given target. Internal use.
            """
            target = gdb.selected_inferior()

            if target.is_valid():
                try:
                    output = gdb.execute('info program', to_string=True)
                    if "not being run" in output:
                        state = "invalid"
                    elif "stopped" in output:
                        state = "stopped"
                except gdb.error as e:
                    if 'Selected thread is running.' == str(e):
                        state = "running"
            else:
                state = "invalid"

            return state

        def get_register(self, reg_name):
            arch = self.get_arch()

            if arch == "x86_64":
                reg = self.get_register_x86_64(reg_name)
            elif arch == "x86":
                reg = self.get_register_x86(reg_name)
            elif arch == "arm":
                reg = self.get_register_arm(reg_name)
            elif arch == "powerpc":
                reg = self.get_register_powerpc(reg_name)
            else:
                raise UnknownArchitectureException()

            return reg

        def get_registers_x86_64(self):
            # Get regular registers
            regs = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15',
                    'cs','ds','es','fs','gs','ss']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = self.get_register_x86_64(reg)
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'

            # Get flags
            try:
                vals['rflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
            except:
                log.debug('Failed getting reg: eflags')
                vals['rflags'] = 'N/A'

            # Get SSE registers
            try:
                sse = self.get_registers_sse(16)
                vals = dict(list(vals.items()) + list(sse.items()))
            except gdb.error:
                log.exception("Failed to get SSE registers")

            # Get FPU registers
            try:
                fpu = self.get_registers_fpu()
                vals = dict(list(vals.items()) + list(fpu.items()))
            except gdb.error:
                log.exception("Failed to get FPU registers")

            return vals

        def get_register_x86_64(self, reg):
            return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF

        def get_registers_x86(self):
            # Get regular registers
            regs = ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip','cs','ds','es','fs','gs','ss']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = self.get_register_x86(reg)
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'

            # Get flags
            try:
                vals['eflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
            except:
                log.debug('Failed getting reg: eflags')
                vals['eflags'] = 'N/A'

            # Get SSE registers
            try:
                sse = self.get_registers_sse(8)
                vals = dict(list(vals.items()) + list(sse.items()))
            except gdb.error:
                log.exception("Failed to get SSE registers")

            # Get FPU registers
            try:
                fpu = self.get_registers_fpu()
                vals = dict(list(vals.items()) + list(fpu.items()))
            except gdb.error:
                log.exception("Failed to get SSE registers")

            return vals

        def get_register_x86(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

        def get_registers_sse(self, num=8):
            # the old way of doing this randomly crashed gdb or threw a python exception
            regs = {}
            for line in gdb.execute('info all-registers', to_string=True).split('\n'):
                m = re.match('^([xyz]mm\d+)\s.*uint128 = (0x[0-9a-f]+)\}', line)
                if m:
                    regs[m.group(1)] = int(m.group(2), 16)
            return regs

        def get_registers_fpu(self):
            regs = {}
            for i in range(8):
                reg = 'st'+str(i)
                try:
                    regs[reg] = int(gdb.execute('info reg '+reg, to_string=True).split()[-1][2:-1], 16)
                except:
                    log.debug('Failed getting reg: ' + reg)
                    regs[reg] = 'N/A'
            return regs

        def get_registers_arm(self):
            log.debug('Getting registers')
            regs = ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6', 'r7','r8','r9','r10','r11','r12']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = self.get_register_arm(reg)
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'
            return vals

        def get_register_arm(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

        def get_registers_powerpc(self):
            log.debug('Getting registers')
            # TODO This could ideally pull from a single definition for the arch
            regs = ['pc','msr','cr','lr', 'ctr',
                    'r0','r1','r2','r3','r4','r5','r6', 'r7',
                    'r8','r9','r10','r11','r12','r13','r14', 'r15',
                    'r16','r17','r18','r19','r20','r21','r22', 'r23',
                    'r24','r25','r26','r27','r28','r29','r30', 'r31']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = self.get_register_powerpc(reg)
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'
            return vals

        def get_register_powerpc(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

        def get_next_instruction(self):
            return self.get_disasm().split('\n')[0].split(':')[1].strip()

        def get_arch(self):
            try:
                arch = gdb.selected_frame().architecture().name()
            except:
                arch = re.search('\(currently (.*)\)', gdb.execute('show architecture', to_string=True)).group(1)
            return self.archs[arch]

        def get_addr_size(self):
            arch = self.get_arch()

            return self.sizes[arch]

        def get_byte_order(self):
            return 'little' if 'little' in gdb.execute('show endian', to_string=True) else 'big'


    class GDBCommand(DebuggerCommand, gdb.Command):
        """
        Debugger command class for GDB
        """
        def __init__(self):
            super(GDBCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)
            self.adaptor = voltron.debugger
            self.registered = False
            self.register_hooks()

        def invoke(self, arg, from_tty):
            self.handle_command(arg)

        def register_hooks(self):
            if not self.registered:
                gdb.events.stop.connect(self.stop_handler)
                gdb.events.exited.connect(self.stop_and_exit_handler)
                gdb.events.cont.connect(self.cont_handler)

        def unregister_hooks(self):
            if self.registered:
                gdb.events.stop.disconnect(self.stop_handler)
                gdb.events.exited.disconnect(self.stop_and_exit_handler)
                gdb.events.cont.disconnect(self.cont_handler)
                self.registered = False

        def stop_handler(self, event):
            self.adaptor.update_state()
            voltron.server.dispatch_queue()
            log.debug('Inferior stopped')

        def exit_handler(self, event):
            log.debug('Inferior exited')
            voltron.server.stop()

        def stop_and_exit_handler(self, event):
            log.debug('Inferior stopped and exited')
            self.stop_handler(event)
            self.exit_handler(event)

        def cont_handler(self, event):
            log.debug('Inferior continued')
            if not voltron.server.is_running:
                voltron.server.start()


    class GDBAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'gdb'
        adaptor_class = GDBAdaptor
        command_class = GDBCommand
