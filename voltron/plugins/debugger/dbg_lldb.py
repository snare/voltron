from __future__ import print_function

import struct
import logging
import threading
from collections import namedtuple

from voltron.api import *
from voltron.plugin import *
from voltron.dbg import *

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

        def normalize_triple(self, triple):
            """
            Returns a (cpu, platform, abi) triple

            Returns None for any fields that can't be elided
            """

            arch, platform, abi = triple.split("-")
            if arch == "x86_64h":
                arch = "x86_64"
            return (arch, platform, abi)

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
                d["arch"], _, _ = self.normalize_triple(t.triple)
            except:
                d["arch"] = None
            if d["arch"] == 'i386':
                d["arch"] = 'x86'
            d["byte_order"] = 'little' if t.byte_order == lldb.eByteOrderLittle else 'big'
            d["addr_size"] = t.addr_size

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
        def registers(self, target_id=0, thread_id=None, registers=[]):
            """
            Get the register values for a given target/thread.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get the target
            target = self.host.GetTargetAtIndex(target_id)
            t_info = self._target(target_id)

            # get the thread
            if not thread_id:
                thread_id = target.process.selected_thread.id
            try:
                thread = target.process.GetThreadByID(thread_id)
            except:
                raise NoSuchThreadException()

            # if we got 'sp' or 'pc' in registers, change it to whatever the right name is for the current arch
            if t_info['arch'] in self.reg_names:
                if 'pc' in registers:
                    registers.remove('pc')
                    registers.append(self.reg_names[t_info['arch']]['pc'])
                if 'sp' in registers:
                    registers.remove('sp')
                    registers.append(self.reg_names[t_info['arch']]['sp'])
            else:
                raise Exception("Unsupported architecture: {}".format(t_info['arch']))

            # get the registers
            log.warn("thing: {}".format(registers))
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
                        val = reg.GetValueAsUnsigned()
                    except:
                        reg = None
                if registers == [] or reg.name in registers:
                    regs[reg.name] = val

            return regs

        @validate_busy
        @validate_target
        @lock_host
        def stack_pointer(self, target_id=0, thread_id=None):
            """
            Get the value of the stack pointer register.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get registers and targets
            regs = self.registers(target_id=target_id, thread_id=thread_id)
            target = self._target(target_id=target_id)

            # get stack pointer register
            if target['arch'] in self.reg_names:
                sp_name = self.reg_names[target['arch']]['sp']
                sp = regs[sp_name]
            else:
                raise Exception("Unsupported architecture: {}".format(target['arch']))

            return (sp_name, sp)

        @validate_busy
        @validate_target
        @lock_host
        def program_counter(self, target_id=0, thread_id=None):
            """
            Get the value of the program counter register.

            `target_id` is a target ID (or None for the first target)
            `thread_id` is a thread ID (or None for the selected thread)
            """
            # get registers and targets
            regs = self.registers(target_id=target_id, thread_id=thread_id)
            target = self._target(target_id=target_id)

            # get stack pointer register
            if target['arch'] in self.reg_names:
                pc_name = self.reg_names[target['arch']]['pc']
                pc = regs[pc_name]
            else:
                raise Exception("Unsupported architecture: {}".format(target['arch']))

            return (pc_name, pc)

        @validate_busy
        @validate_target
        @lock_host
        def memory(self, address, length, target_id=0):
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
        def disassemble(self, target_id=0, address=None, count=None):
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
            res = lldb.SBCommandReturnObject()
            output = self.command('disassemble -s {} -c {}'.format(address, count))

            return output

        @validate_busy
        @validate_target
        @lock_host
        def dereference(self, pointer, target_id=0):
            """
            Recursively dereference a pointer for display
            """
            t = self.host.GetTargetAtIndex(target_id)
            error = lldb.SBError()

            addr = pointer
            chain = []

            # recursively dereference
            while True:
                ptr = t.process.ReadPointerFromMemory(addr, error)
                if error.Success():
                    if ptr in chain:
                        chain.append(('circular', 'circular'))
                        break
                    chain.append(('pointer', addr))
                    addr = ptr
                else:
                    break

            # get some info for the last pointer
            # first try to resolve a symbol context for the address
            p, addr = chain[-1]
            sbaddr = lldb.SBAddress(addr, t)
            ctx = t.ResolveSymbolContextForAddress(sbaddr, lldb.eSymbolContextEverything)
            if ctx.IsValid() and ctx.GetSymbol().IsValid():
                # found a symbol, store some info and we're done for this pointer
                fstart = ctx.GetSymbol().GetStartAddress().GetLoadAddress(t)
                offset = addr - fstart
                chain.append(('symbol', '{} + 0x{:X}'.format(ctx.GetSymbol().name, offset)))
                log.debug("symbol context: {}".format(str(chain[-1])))
            else:
                # no symbol context found, see if it looks like a string
                log.debug("no symbol context")
                s = t.process.ReadCStringFromMemory(addr, 256, error)
                for i in range(0, len(s)):
                    if ord(s[i]) >= 128:
                        s = s[:i]
                        break
                if len(s):
                    chain.append(('string', s))

            return chain

        @lock_host
        def command(self, command=None):
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


        @validate_busy
        @validate_target
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
            t = self.host.GetTargetAtIndex(target_id)
            s = lldb.SBStream()

            for i in range(0, t.GetNumBreakpoints()):
                b = t.GetBreakpointAtIndex(i)
                locations = []

                for j in range(0, b.GetNumLocations()):
                    l = b.GetLocationAtIndex(j)
                    s.Clear()
                    l.GetAddress().GetDescription(s)
                    desc = s.GetData()
                    locations.append({
                        'address':  l.GetLoadAddress(),
                        'name':     desc
                    })

                breakpoints.append({
                    'id':           b.id,
                    'enabled':      b.enabled,
                    'one_shot':     b.one_shot,
                    'hit_count':    b.GetHitCount(),
                    'locations':    locations
                })

            return breakpoints

        def register_command_plugin(self, name, cls):
            """
            Register a command plugin with the LLDB adaptor.
            """
            # make sure we have a commands object
            if not voltron.commands:
                voltron.commands = namedtuple('VoltronCommands', [])

            # method invocation creator
            def create_invocation(obj):
                def invoke(debugger, command, result, env_dict):
                    obj.invoke(*command.split())
                return invoke

            # store the invocation in `voltron.commands` to pass to LLDB
            setattr(voltron.commands, name, create_invocation(cls()))

            # register the invocation as a command script handler thing
            self.host.HandleCommand("command script add -f voltron.commands.{} {}".format(name, name))


    class LLDBAdaptorPlugin(DebuggerAdaptorPlugin):
        host = 'lldb'
        adaptor_class = LLDBAdaptor
