from __future__ import print_function

import os
import sys
import gdb
import logging

from voltron.cmd import *

log = logging.getLogger('voltron')

class VoltronGDBCommand (VoltronCommand, gdb.Command):
    def __init__(self):
        super(VoltronCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)
        self.running = False

    def invoke(self, arg, from_tty):
        self.handle_command(arg)

    def register_hooks(self):
        gdb.events.stop.connect(self.stop_handler)

    def unregister_hooks(self):
        gdb.events.stop.disconnect(self.stop_handler)

    def stop_handler(self, event):
        self.update()

    def get_registers(self):
        log.debug('Getting registers')
        regs = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15',
                'cs','ds','es','fs','gs','ss']
        vals = {}
        for reg in regs:
            try:
                vals[reg] = int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'
        try:
            vals['rflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
        except:
            log.debug('Failed getting reg: eflags')
            vals['rflags'] = 'N/A'
        regs = ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8','xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15']
        for reg in regs:
            try:
                vals[reg] = int(str(gdb.parse_and_eval('$'+reg+'.uint128')), 16) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'
        regs = ['st0','st1','st2','st3','st4','st5','st6','st7']
        for reg in regs:
            try:
                vals[reg] = int(gdb.execute('info reg '+reg, to_string=True).split()[-1][2:-1], 16)
            except:
                log.debug('Failed getting reg: ' + reg)
                vals[reg] = 'N/A'
        log.debug('Got registers: ' + str(vals))
        return vals

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF

    def get_disasm(self):
        log.debug('Getting disasm')
        res = gdb.execute('x/{}i $rip'.format(DISASM_MAX), to_string=True)
        return res

    def get_stack(self):
        log.debug('Getting stack')
        rsp = int(gdb.parse_and_eval('(long long)$rsp')) & 0xFFFFFFFFFFFFFFFF
        res = str(gdb.selected_inferior().read_memory(rsp, STACK_MAX*16))
        return res

    def get_backtrace(self):
        log.debug('Getting backtrace')
        res = gdb.execute('bt', to_string=True)
        return res

    def get_cmd_output(self, cmd=None):
        if cmd:
            log.debug('Getting command output: ' + cmd)
            res = gdb.execute(cmd, to_string=True)
        else:
            res = "<No command>"
        return res


if __name__ == "__main__":
    log.debug('Loading GDB command')
    print("Voltron loaded.")
    inst = VoltronGDBCommand()

