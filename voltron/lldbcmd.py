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

    def get_arch(self):
        arch = self.debugger.GetTargetAtIndex(0).triple.split('-')[0]
        if arch == 'x86_64':
            return 'x64'
        elif arch == 'i386':
            return 'x86'
        elif arch == 'arm':
            return 'arm'

    def get_frame(self):
        return self.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

    def get_next_instruction(self):
        target = self.debugger.GetTargetAtIndex(0)
        pc = lldb.SBAddress(self.get_pc(), target)
        inst = target.ReadInstructions(pc, 1)
        return str(inst).split(':')[1].strip()

    def get_registers(self):
        log.debug('Getting registers')

        # Get registers
        objs = self.get_frame().GetRegisters()
        objs = list(objs[0]) + list(objs[1]) + list(objs[2])
        regs = {}
        for reg in objs:
            val = 'n/a'
            if reg.value != None:
                val = int(reg.value, 16)
            regs[reg.name] = val
        for i in range(7):
            regs['st'+str(i)] = regs['stmm'+str(i)]

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
        arch = self.get_arch()
        if arch == 'x64':
            sp = self.get_register('rsp')
        elif arch == 'x86':
            sp = self.get_register('esp')
        elif arch == 'arm':
            sp = self.get_register('sp')
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(sp, STACK_MAX*16, error)
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