from __future__ import print_function

import lldb
import logging
import logging.config

from .cmd import *
from .comms import *
from .common import *

log = configure_logging()
inst = None

class VoltronLLDBCommand (VoltronCommand):
    def __init__(self, debugger, dict):
        self.debugger = debugger
        debugger.HandleCommand('command script add -f dbgentry.lldb_invoke voltron')
        self.running = False
        self.server = None
        self.helper = None

    def invoke(self, debugger, command, result, dict):
        self.handle_command(command)

    def start(self):
        if self.server == None:
            self.start_server()
        super(VoltronLLDBCommand, self).start()

    def register_hooks(self):
        lldb.debugger.HandleCommand('target stop-hook add -o \'voltron update\'')

    def unregister_hooks(self):
        # XXX: Fix this so it only removes our stop-hook
        lldb.debugger.HandleCommand('target stop-hook delete')

    def find_helper(self):
        arch = lldb.debugger.GetTargetAtIndex(0).triple.split('-')[0]
        for cls in LLDBHelper.__inheritors__:
            if hasattr(cls, 'archs') and arch in cls.archs:
                inst = cls()
                return inst
        raise LookupError('No helper found for arch {}'.format(arch))


class LLDBHelper (DebuggerHelper):
    def get_arch(self):
        return lldb.debugger.GetTargetAtIndex(0).triple.split('-')[0]

    def get_frame(self):
        return lldb.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

    def get_next_instruction(self):
        target = lldb.debugger.GetTargetAtIndex(0)
        pc = lldb.SBAddress(self.get_pc(), target)
        inst = target.ReadInstructions(pc, 1)
        return str(inst).split(':')[1].strip()

    def get_registers(self):
        log.debug('Getting registers')

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
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(self.get_sp(), STACK_MAX*16, error)
        return res

    def get_backtrace(self):
        log.debug('Getting backtrace')
        res = self.get_cmd_output('bt')
        return res

    def get_cmd_output(self, cmd=None):
        if cmd:
            log.debug('Getting command output: ' + cmd)
            res = lldb.SBCommandReturnObject()
            lldb.debugger.GetCommandInterpreter().HandleCommand(cmd, res)
            res = res.GetOutput()
        else:
            res = "<No command>"
        return res


class LLDBHelperX86 (LLDBHelper):
    archs = ['i386']
    arch_group = 'x86'
    pc = 'eip'
    sp = 'esp'


class LLDBHelperX64 (LLDBHelper):
    archs = ['x86_64']
    arch_group = 'x64'
    pc = 'rip'
    sp = 'rsp'


class LLDBHelperARM (LLDBHelper):
    archs = ['arm']
    arch_group = 'arm'
    pc = 'pc'
    sp = 'sp'

