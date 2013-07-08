from __future__ import print_function

import lldb
import logging

from cmd import *
from comms import *

log = logging.getLogger('voltron')

inst = None

# Called when the module is loaded into lldb and initialised
def __lldb_init_module(debugger, dict):
    global inst
    log.debug('Loading LLDB command')
    inst = VoltronLLDBCommand(debugger, dict)

# Called when the command is invoked
def lldb_invoke(debugger, command, result, dict):
    inst.invoke(debugger, command, result, dict)

class VoltronLLDBCommand (VoltronCommand):
    def __init__(self, debugger, dict):
        self.debugger = debugger
        debugger.HandleCommand('command script add -f lldbcmd.lldb_invoke voltron')
        self.running = False

    def invoke(self, debugger, command, result, dict):
        self.debugger = debugger
        self.handle_command(command)

    def register_hooks(self):
        self.debugger.HandleCommand('target stop-hook add -o \'voltron update\'')

    def unregister_hooks(self):
        # XXX: Fix this so it only removes our stop-hook
        self.debugger.HandleCommand('target stop-hook delete')

    def get_frame(self):
        return self.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

    def get_registers(self):
        log.debug('Getting registers')
        frame = self.get_frame()
        regs = {x.name:int(x.value, 16) for x in list(list(frame.GetRegisters())[0])}
        return regs

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return self.get_registers()[reg]

    def get_disasm(self):
        log.debug('Getting disasm')
        res = self.get_cmd_output('disassemble -c {}'.format(DISASM_MAX))
        return res

    def get_stack(self):
        log.debug('Getting stack')
        rsp = self.get_register('rsp')
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(rsp, STACK_MAX*16, error)
        return res

    def get_backtrace(self):
        log.debug('Getting backtrace')
        res = self.get_cmd_output('bt')
        return res

    def get_cmd_output(self, cmd=None):
        if cmd:
            log.debug('Getting command output: ' + cmd)
            res = lldb.SBCommandReturnObject()
            self.debugger.GetCommandInterpreter().HandleCommand(cmd, res)
            res = res.GetOutput()
        else:
            res = "<No command>"
        return res