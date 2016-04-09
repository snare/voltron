from __future__ import print_function

import logging
import threading
import re
import struct
import six
import array

from voltron.api import *
from voltron.plugin import *
from voltron.dbg import *

try:
    in_windbg = False
    import pykd
    try:
        import vtrace
    except:
        in_windbg = True
except ImportError:
    pass

log = logging.getLogger('debugger')


if in_windbg:
    class WinDbgAdaptor(DebuggerAdaptor):
        sizes = {
            'x86': 4,
            'x86_64': 8,
        }
        max_deref = 24
        max_string = 128

        def __init__(self, *args, **kwargs):
            self.listeners = []
            self.host_lock = threading.RLock()
            self.host = pykd

        def version(self):
            """
            Get the debugger's version.

            Returns a string containing the debugger's version
            (e.g. 'Microsoft (R) Windows Debugger Version whatever, pykd 0.3.0.38')
            """
            try:
                [windbg] = [line for line in pykd.dbgCommand('version').split('\n') if 'Microsoft (R) Windows Debugger Version' in line]
            except:
                windbg = 'WinDbg <unknown>'
            return '{}, {}'.format(windbg, 'pykd {}'.format(pykd.version))

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
            # get target properties
            d = {}
            d["id"] = pykd.getCurrentProcessId()
            d["num"] = d['id']

            # get target state
            d["state"] = self._state()

            d["file"] = pykd.getProcessExeName()

            # get arch
            d["arch"] = self.get_arch()
            d['byte_order'] = self.get_byte_order()
            d['addr_size'] = self.get_addr_size()

            return d

        @lock_host
        def target(self, target_id=0):
            """
            Return information about the current inferior.

            We only support querying the current inferior with WinDbg.

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
                vals = {}
                for reg in registers:
                    vals[reg] = pykd.reg(reg)
            else:
                log.debug('Getting registers for arch {}'.format(arch))
                if arch == "x86_64":
                    reg_names = ['rax', 'rbx', 'rcx', 'rdx', 'rbp', 'rsp', 'rdi', 'rsi', 'rip', 'r8', 'r9', 'r10',
                                 'r11', 'r12', 'r13', 'r14', 'r15', 'cs', 'ds', 'es', 'fs', 'gs', 'ss']
                elif arch == "x86":
                    reg_names = ['eax', 'ebx', 'ecx', 'edx', 'ebp', 'esp', 'edi', 'esi', 'eip', 'cs', 'ds', 'es',
                                 'fs', 'gs', 'ss']
                else:
                    raise UnknownArchitectureException()

                vals = {}
                for reg in reg_names:
                    try:
                        vals[reg] = pykd.reg(reg)
                    except:
                        log.debug('Failed getting reg: ' + reg)
                        vals[reg] = 'N/A'

                # Get flags
                try:
                    vals['rflags'] = pykd.reg(reg)
                except:
                    log.debug('Failed getting reg: eflags')
                    vals['rflags'] = 'N/A'

                # Get SSE registers
                try:
                    vals.update(self.get_registers_sse(16))
                except:
                    log.exception("Failed to get SSE registers")

                # Get FPU registers
                try:
                    vals.update(self.get_registers_fpu())
                except:
                    log.exception("Failed to get FPU registers")

            return vals

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
                sp = pykd.reg(sp_name)
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
                pc = pykd.reg(pc_name)
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
            memory = array.array('B', pykd.loadBytes(address, length)).tostring()

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
            if address is None:
                pc_name, address = self.program_counter(target_id=target_id)

            # disassemble
            output = pykd.dbgCommand('u 0x{:x} l{}'.format(address, count))

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
            for i in range(0, self.max_deref):
                try:
                    [ptr] = pykd.loadPtrs(addr, 1)
                    if ptr in chain:
                        break
                    chain.append(('pointer', addr))
                    addr = ptr
                except:
                    log.exception("Dereferencing pointer 0x{:X}".format(addr))
                    break

            # get some info for the last pointer
            # first try to resolve a symbol context for the address
            if len(chain):
                p, addr = chain[-1]
                output = pykd.findSymbol(addr)
                sym = True
                try:
                    # if there's no symbol found, pykd returns a hex string of the address
                    if int(output, 16) == addr:
                        sym = False
                        log.debug("no symbol context")
                except:
                    pass

                if sym:
                    chain.append(('symbol', output.strip()))
                else:
                    log.debug("no symbol context")
                    mem = pykd.loadBytes(addr, 2)
                    if mem[0] < 127:
                        if mem[1] == 0:
                            a = []
                            for i in range(0, self.max_string, 2):
                                mem = pykd.loadBytes(addr + i, 2)
                                if mem == [0, 0]:
                                    break
                                a.extend(mem)
                            output = array.array('B', a).tostring().decode('UTF-16').encode('latin1')
                            chain.append(('unicode', output))
                        else:
                            output = pykd.loadCStr(addr)
                            chain.append(('string', output))

            log.debug("chain: {}".format(chain))
            return chain

        @lock_host
        def command(self, command=None):
            """
            Execute a command in the debugger.

            `command` is the command string to execute.
            """
            if command:
                res = pykd.dbgCommand(command)
            else:
                raise Exception("No command specified")

            return res

        @lock_host
        def disassembly_flavor(self):
            """
            Return the disassembly flavor setting for the debugger.

            Returns 'intel' or 'att'
            """
            return 'intel'

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

            for i in range(0, pykd.getNumberBreakpoints()):
                b = pykd.getBp(i)
                addr = b.getOffset()

                name = hex(addr)
                try:
                    name = pykd.findSymbol(addr)
                except:
                    log.exception("No symbol found for address {}".format(addr))
                    pass

                breakpoints.append({
                    'id':           i,
                    'enabled':      True,
                    'one_shot':     False,
                    'hit_count':    '-',
                    'locations':    [{
                        "address":  addr,
                        "name":     name
                    }]
                })

            return breakpoints

        def capabilities(self):
            """
            Return a list of the debugger's capabilities.

            Thus far only the 'async' capability is supported. This indicates
            that the debugger host can be queried from a background thread,
            and that views can use non-blocking API requests without queueing
            requests to be dispatched next time the debugger stops.
            """
            return ['async']

        #
        # Private functions
        #

        def _state(self):
            """
            Get the state of a given target. Internal use.
            """
            s = pykd.getExecutionStatus()
            if s == pykd.executionStatus.Break:
                state = 'stopped'
            elif s == pykd.executionStatus.Go:
                state = 'running'
            else:
                state = 'invalid'

            return state

        def get_registers_sse(self, num=8):
            regs = {}
            for i in range(0, 16):
                try:
                    reg = 'xmm{}'.format(i)
                    regs[reg] = pykd.reg(reg)
                except:
                    break
            return regs

        def get_registers_fpu(self):
            regs = {}
            for i in range(0, 8):
                try:
                    reg = 'st{}'.format(i)
                    regs[reg] = pykd.reg(reg)
                except:
                    break
            return regs

        def get_next_instruction(self):
            return str(pykd.disasm())

        def get_arch(self):
            t = pykd.getCPUType()
            if t == pykd.CPUType.I386:
                return 'x86'
            else:
                return 'x86_64'
            return arch

        def get_addr_size(self):
            arch = self.get_arch()
            return self.sizes[arch]

        def get_byte_order(self):
            return 'little'


    class EventHandler(pykd.eventHandler):
        """
        Event handler for WinDbg/PyKD events.
        """
        def __init__(self, adaptor, *args, **kwargs):
            super(EventHandler, self).__init__(*args, **kwargs)
            self.adaptor = adaptor

        def onExecutionStatusChange(self, status):
            if status == pykd.executionStatus.Break:
                self.adaptor.update_state()
                voltron.server.dispatch_queue()


    class WinDbgCommand(DebuggerCommand):
        """
        Debugger command class for WinDbg
        """
        def __init__(self):
            super(WinDbgCommand, self).__init__()
            self.register_hooks()

        def invoke(self, debugger, command, result, dict):
            self.handle_command(command)

        def register_hooks(self):
            self.handler = EventHandler(self.adaptor)

        def unregister_hooks(self):
            del self.handler
            self.handler = None


    class WinDbgAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'windbg'
        adaptor_class = WinDbgAdaptor
        command_class = WinDbgCommand
