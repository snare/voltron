from __future__ import print_function

import logging
import threading

from voltron.api import *
from voltron.plugin import *
from voltron.debugger import *

try:
    import lldb
    HAVE_LLDB = True
except ImportError:
    HAVE_LLDB = False

log = logging.getLogger('debugger')

if HAVE_LLDB:

    class LLDBAdaptor(DebuggerAdaptor):
        """
        The interface with an instance of LLDB
        """
        def __init__(self, host=None):
            self.listeners = []
            self.host_lock = threading.RLock()
            if host:
                log.debug("Passed a debugger host")
                self.host = host
            elif lldb.debugger:
                log.debug("lldb.debugger is valid - probably running inside LLDB")
                self.host = lldb.debugger
            else:
                log.debug("No debugger host found - creating one")
                self.host = lldb.SBDebugger.Create()
                self.host.SetAsync(False)

        @property
        def host(self):
            """
            Get the debugger host object that this adaptor talks to. Used by
            custom API plugins to talk directly to the debugger.
            """
            return self._host

        @host.setter
        def host(self, value):
            self._host = value

        def version(self):
            """
            Get the debugger's version.

            Returns a string containing the debugger's version
            (e.g. 'lldb-310.2.37')
            """
            return self.host.GetVersionString()

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
            t = self.host.GetTargetAtIndex(target_id)

            # get target properties
            d = {}
            d["id"] = target_id
            d["state"] = self.host.StateAsCString(t.process.GetState())
            d["file"] = t.GetExecutable().fullpath
            try:
                d["arch"] = t.triple.split('-')[0]
            except:
                d["arch"] = None

            return d

        @lock_host
        def target(self, target_id=0):
            """
            Return information about the specified target.
            """
            return self._target(target_id=target_id)

        @lock_host
        def targets(self, target_ids=None):
            """
            Return information about the debugger's current targets.

            `target_ids` is an array of target IDs (or None for all targets)

            Returns data in the following structure:
            [
                {
                    "id":       0,         # ID that can be used in other funcs
                    "file":     "/bin/ls", # target's binary file
                    "arch":     "x86_64",  # target's architecture
                    "state:     "stopped"  # state
                }
            ]
            """
            # initialise returned data
            targets = []

            # if we didn't get any target IDs, get info for all targets
            if not target_ids:
                n = self.host.GetNumTargets()
                target_ids = range(n)

            # iterate through targets
            log.debug("Getting info for {} targets".format(len(target_ids)))
            for i in target_ids:
                targets.append(self._target(i))

            return targets

        @validate_target
        @lock_host
        def state(self, target_id=0):
            """
            Get the state of a given target.

            `target_id` is a target ID (or None for the first target)
            """
            target = self.host.GetTargetAtIndex(target_id)
            state = self.host.StateAsCString(target.process.GetState())

            return state

        @validate_busy
        @validate_target
        @lock_host
        def read_registers(self, target_id=0, thread_id=None):
            """
            Get the register values for a given target/thread.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get the target
            target = self.host.GetTargetAtIndex(target_id)

            # get the thread
            if not thread_id:
                thread_id = target.process.selected_thread.id
            try:
                thread = target.process.GetThreadByID(thread_id)
            except:
                raise NoSuchThreadException()

            # get the registers
            regs = thread.GetFrameAtIndex(0).GetRegisters()

            # extract the actual register values
            objs = []
            for i in xrange(len(regs)):
                objs += regs[i]
            regs = {}
            for reg in objs:
                val = 'n/a'
                if reg.value != None:
                    try:
                        val = int(reg.value, 16)
                    except:
                        try:
                            val = int(reg.value)
                        except Exception as e:
                            log.error("Exception converting register value: " + str(e))
                            val = 0
                regs[reg.name] = val

            return regs

        @validate_busy
        @validate_target
        @lock_host
        def read_stack_pointer(self, target_id=0, thread_id=None):
            """
            Get the value of the stack pointer register.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get registers and targets
            regs = self.read_registers(target_id=target_id, thread_id=thread_id)
            target = self._target(target_id=target_id)

            # get stack pointer register
            if target['arch'] in self.reg_names:
                sp_name = self.reg_names[target['arch']]['sp']
                sp = regs[sp_name]
            else:
                raise Exception("Unsupported architecture: {}".format(target['arch']))

            return sp

        @validate_busy
        @validate_target
        @lock_host
        def read_program_counter(self, target_id=0, thread_id=None):
            """
            Get the value of the program counter register.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get registers and targets
            regs = self.read_registers(target_id=target_id, thread_id=thread_id)
            target = self._target(target_id=target_id)

            # get stack pointer register
            if target['arch'] in self.reg_names:
                pc_name = self.reg_names[target['arch']]['pc']
                pc = regs[pc_name]
            else:
                raise Exception("Unsupported architecture: {}".format(target['arch']))

            return pc

        @validate_busy
        @validate_target
        @lock_host
        def read_memory(self, address, length, target_id=0):
            """
            Get the register values for .

            `address` is the address at which to start reading
            `length` is the number of bytes to read
            `target_id` is a target ID (or None for the first target)
            """
            # get the target
            target = self.host.GetTargetAtIndex(target_id)

            # read memory
            log.debug('Reading 0x{:x} bytes of memory at 0x{:x}'.format(length, address))

            error = lldb.SBError()
            memory = target.process.ReadMemory(address, length, error)

            if not error.Success():
                raise Exception("Failed reading memory: {}".format(error.GetCString()))

            return memory

        @validate_busy
        @validate_target
        @lock_host
        def read_stack(self, length, target_id=0, thread_id=None):
            """
            Get the register values for .

            `length` is the number of bytes to read
            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get the stack pointer
            sp = self.read_stack_pointer(target_id=target_id, thread_id=thread_id)

            # read memory
            memory = self.read_memory(sp, length, target_id=target_id)

            return memory

        @validate_busy
        @validate_target
        @lock_host
        def disassemble(self, target_id=0, address=None, count=None):
            """
            Get a disassembly of the instructions at the given address.

            `address` is the address at which to disassemble. If None, the
            current program counter is used.
            `count` is the number of instructions to disassemble.
            """
            # make sure we have an address
            if address == None:
                address = self.read_program_counter(target_id=target_id)

            # disassemble
            res = lldb.SBCommandReturnObject()
            output = self.execute_command('disassemble -s {} -c {}'.format(address, count))

            return output

        @lock_host
        def execute_command(self, command=None):
            """
            Execute a command in the debugger.

            `command` is the command string to execute.
            """
            # for some reason this doesn't work - figure it out
            if command:
                res = lldb.SBCommandReturnObject()
                ci = self.host.GetCommandInterpreter()
                ci.HandleCommand(str(command), res)
                if res.Succeeded():
                    return res.GetOutput().strip()
                else:
                    raise Exception(res.GetError().strip())
            else:
                raise Exception("No command specified")

        @lock_host
        def disassembly_flavor(self):
            """
            Return the disassembly flavor setting for the debugger.

            Returns 'intel' or 'att'
            """
            res = lldb.SBCommandReturnObject()
            ci = self.host.GetCommandInterpreter()
            ci.HandleCommand('settings show target.x86-disassembly-flavor', res)
            if res.Succeeded():
                output = res.GetOutput().strip()
                flavor = output.split()[-1]
                if flavor == 'default':
                    flavor = 'att'
            else:
                raise Exception(res.GetError().strip())

            return flavor


    class LLDBAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'lldb'
        adaptor_class = LLDBAdaptor
