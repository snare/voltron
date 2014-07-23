from __future__ import print_function

import logging
import logging.config
import threading

from voltron.api import *
from voltron.plugin import *

try:
    import lldb
    HAVE_LLDB = True
except ImportError:
    HAVE_LLDB = False

log = logging.getLogger('debugger')

if HAVE_LLDB:
    class LLDBException(Exception):
        """
        Raised when an LLDB operation fails
        """
        def __init__(self, error=None):
            pass


    class LLDBAdaptor (object):
        """
        The interface with an instance of LLDB
        """
        reg_names = {
            "x86":      {"pc": "eip", "sp": "esp"},
            "x86_64":   {"pc": "rip", "sp": "rsp"},
            "armv6":    {"pc": "pc", "sp": "sp"},
            "armv7":    {"pc": "pc", "sp": "sp"},
            "armv7s":   {"pc": "pc", "sp": "sp"},
            "arm64":    {"pc": "pc", "sp": "sp"},
        }
        def __init__(self, host=None):
            self.wait_event = threading.Event()
            self.host_lock = threading.RLock()
            self.listeners = []
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

        def validate_target(func, *args, **kwargs):
            """
            A decorator that ensures that the specified target_id exists and
            is valid.

            Expects the target ID to be either the 'target_id' param in kwargs,
            or the first positional parameter.

            Raises a NoSuchTargetException if the target does not exist.
            """
            def inner(self, *args, **kwargs):
                # find the target param
                target_id = None
                if 'target_id' in kwargs and kwargs['target_id'] != None:
                    target_id = kwargs['target_id']
                elif len(args):
                    target_id = args[0]
                else:
                    target_id = 0

                # if there was a target specified, check that it's valid
                if not self.target_is_valid(target_id):
                    raise NoSuchTargetException()

                # call the function
                return func(self, *args, **kwargs)
            return inner

        def validate_busy(func, *args, **kwargs):
            """
            A decorator that raises an exception if the specified target is busy.

            Expects the target ID to be either the 'target_id' param in kwargs,
            or the first positional parameter.

            Raises a TargetBusyException if the target does not exist.
            """
            def inner(self, *args, **kwargs):
                # find the target param
                target_id = None
                if 'target_id' in kwargs and kwargs['target_id'] != None:
                    target_id = kwargs['target_id']
                elif len(args):
                    target_id = args[0]
                else:
                    target_id = 0

                # if there was a target specified, ensure it's not busy
                if self.target_is_busy(target_id):
                    raise TargetBusyException()

                # call the function
                return func(self, *args, **kwargs)
            return inner

        def lock_host(func, *args, **kwargs):
            """
            A decorator that acquires a lock before accessing the debugger to
            avoid API locking related errors with LLDB
            """
            def inner(self, *args, **kwargs):
                print("locking host")
                self.host_lock.acquire()
                res = func(self, *args, **kwargs)
                self.host_lock.release()
                print("unlocking host")
                return res
            return inner

        def target_exists(self, target_id=0):
            """
            Returns True or False indicating whether or not the specified
            target is present and valid.

            `target_id` is a target ID (or None for the first target)
            """
            try:
                target = self._target(target_id=target_id)
            except Exception, e:
                log.error("Exception checking if target exists: {} {}".format(type(e), e))
                return False
            return target != None

        def target_is_valid(self, target_id=0):
            """
            Returns True or False indicating whether or not the specified
            target is present and valid.

            `target_id` is a target ID (or None for the first target)
            """
            try:
                target = self._target(target_id=target_id)
            except:
                return False
            return target['state'] != "invalid"

        def target_is_busy(self, target_id=0):
            """
            Returns True or False indicating whether or not the specified
            target is busy.

            `target_id` is a target ID (or None for the first target)
            """
            try:
                target = self._target(target_id=target_id)
            except:
                raise NoSuchTargetException()
            return target['state'] == "running"

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

        def target(self, target_id=0):
            """
            Return information about the specified target.

            Same as `target` but the target_id is validated.
            """
            return self._target(target_id=target_id)

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
            thread = target.process.GetThreadByID(thread_id)

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

        #
        # Other methods
        #

        def add_listener(self, callback, state_changes=["stopped"]):
            """
            Add a listener for state changes.
            """
            self.listeners.append({"callback": callback, "state_changes": state_changes})

        def remove_listener(self, callback):
            """
            Remove a listener.
            """
            listeners = filter(lambda x: x['callback'] == callback, self.listeners)
            for l in listeners:
                self.listeners.remove(l)

        def update_state(self):
            """
            Notify all the listeners (probably `wait` plugins) that the state
            has changed.

            This is called by the debugger's stop-hook.
            """
            for listener in self.listeners:
                listener['callback']()



    class LLDBAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'lldb'
        adaptor_class = LLDBAdaptor