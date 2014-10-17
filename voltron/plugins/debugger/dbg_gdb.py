from __future__ import print_function

import logging
import threading
import re

from voltron.api import *
from voltron.plugin import *
from voltron.debugger import *

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
            'armv4t': 'arm', 'armv5': 'arm', 'armv5t': 'arm', 'armv5te': 'arm'
        }

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
            lines = filter(lambda x: x != '', gdb.execute('info inferiors', to_string=True).split('\n'))
            if len(lines) > 1:
                info = filter(lambda x: '*' in x[0], map(lambda x: x.split(), lines[1:]))
                d["file"] = info[0][-1]
            else:
                log.debug("No inferiors in `info inferiors`")
                raise NoSuchTargetException()

            # get arch
            d["arch"] = self.get_arch()

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
        def registers(self, target_id=0, thread_id=None):
            """
            Get the register values for a given target/thread.
            """

            arch = self.get_arch()
            log.debug('Getting registers for arch {}'.format(arch))
            if arch == "x86_64":
                regs = self.get_registers_x86_64()
            elif arch == "x86":
                regs = self.get_registers_x86()
            elif arch == "arm":
                regs = self.get_registers_arm()
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

            return sp

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

            return pc

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
            memory = str(gdb.selected_inferior().memory(address, length))
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
            sp = self.stack_pointer(target_id=target_id, thread_id=thread_id)

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
                address = self.program_counter(target_id=target_id)

            # disassemble
            output = gdb.execute('x/{}i 0x{:x}'.format(count, address), to_string=True)

            return output

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
                except gdb.error, e:
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
                    vals[reg] = int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF
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
            sse = self.get_registers_sse(16)
            vals = dict(list(vals.items()) + list(sse.items()))

            # Get FPU registers
            fpu = self.get_registers_fpu()
            vals = dict(list(vals.items()) + list(fpu.items()))

            return vals

        def get_register_x86_64(self, reg):
            return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF

        def get_registers_x86(self):
            # Get regular registers
            regs = ['eax','ebx','ecx','edx','ebp','esp','edi','esi','eip','cs','ds','es','fs','gs','ss']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
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
            sse = self.get_registers_sse(8)
            vals = dict(list(vals.items()) + list(sse.items()))

            # Get FPU registers
            fpu = self.get_registers_fpu()
            vals = dict(list(vals.items()) + list(fpu.items()))

            return vals

        def get_register_x86(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

        def get_registers_sse(self, num=8):
            # the old way of doing this randomly crashed gdb or threw a python exception
            regs = {}
            for line in gdb.execute('info all-registers', to_string=True).split('\n'):
                m = re.match('^(xmm\d+)\s.*uint128 = (0x[0-9a-f]+)\}', line)
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
                    vals[reg] = int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'
            return vals

        def get_register_arm(self, reg):
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


    class GDBAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'gdb'
        adaptor_class = GDBAdaptor
