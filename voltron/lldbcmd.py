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
        super(VoltronCommand, self).__init__()
        self.debugger = debugger
        lldb.debugger.HandleCommand('command script add -f dbgentry.lldb_invoke voltron')
        self.running = False
        self.server = None
        self.base_helper = LLDBHelper

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


class VoltronLLDBConsoleCommand (VoltronCommand):
    def __init__(self):
        # we just add a reference to a dummy script, and intercept calls to `voltron` in the console
        # this kinda sucks, but it'll do for now
        lldb.debugger.HandleCommand('command script add -f xxx voltron')
        self.running = False
        self.server = None


class LLDBHelper (DebuggerHelper):
    @staticmethod
    def has_target():
        registers = LLDBHelper.get_frame().GetRegisters()
        return len(registers) != 0

    @staticmethod
    def get_frame():
        return lldb.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

    @staticmethod
    def get_arch():
        return lldb.debugger.GetTargetAtIndex(0).triple.split('-')[0]

    @staticmethod
    def helper():
        if LLDBHelper.has_target():
            arch = LLDBHelper.get_arch()
            for cls in LLDBHelper.__subclasses__():
                if hasattr(cls, 'archs') and arch in cls.archs:
                    inst = cls()
                    return inst
            raise LookupError('No helper found for arch {}'.format(arch))
        raise LookupError('No target')

    def get_next_instruction(self):
        target = lldb.debugger.GetTargetAtIndex(0)
        pc = lldb.SBAddress(self.get_pc(), target)
        inst = target.ReadInstructions(pc, 1)
        return str(inst).split(':')[1].strip()

    def get_registers(self):
        log.debug('Getting registers')

        regs = LLDBHelper.get_frame().GetRegisters()
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
                    except Exception, e:
                        log.debug("Exception converting register value: " + str(e))
                        val = 0
            regs[reg.name] = val

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

    def get_memory(self, start, length):
        log.debug('Getting %x + %d' % (start, length))
        error = lldb.SBError()
        res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(start, length, error)
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

    def get_registers(self):
        regs = super(LLDBHelperX86, self).get_registers()
        for i in range(7):
            regs['st'+str(i)] = regs['stmm'+str(i)]
            return regs


class LLDBHelperX64 (LLDBHelperX86, LLDBHelper):
    archs = ['x86_64']
    arch_group = 'x64'
    pc = 'rip'
    sp = 'rsp'


class LLDBHelperARM (LLDBHelper):
    archs = ['armv6', 'armv7', 'armv7s']
    arch_group = 'arm'
    pc = 'pc'
    sp = 'sp'


class LLDBHelperARM64 (LLDBHelper):
    archs = ['arm64']
    arch_group = 'arm64'
    pc = 'pc'
    sp = 'sp'
