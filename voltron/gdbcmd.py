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

    def get_arch(self):
        arch = gdb.selected_frame().architecture().name()
        if arch in ['i386:x86-64', 'i386:x86-64:intel']:
            return 'x64'
        elif arch in ['i386', 'i386:intel', 'i386:x64-32', 'i386:x64-32:intel', 'i8086']:
            return 'x86'
        elif arch in ['arm', 'arm', 'armv2', 'armv2a', 'armv3', 'armv3m', 'armv4', 'armv4t', 'armv5', 'armv5t', 'armv5te']:
            return 'arm'

    def get_registers(self):
        arch = self.get_arch()
        regs = {}
        if arch == 'x64':
            regs = self.get_registers_x64()
        elif arch == 'x86':
            regs = self.get_registers_x86()
        elif arch == 'arm':
            regs = self.get_registers_arm()
        return regs

    def get_registers_x86(self):
        log.debug('Getting registers')

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
        vals = dict(vals.items() + sse.items())

        # Get FPU registers
        fpu = self.get_registers_fpu()
        vals = dict(vals.items() + fpu.items())

        log.debug('Got registers: ' + str(vals))
        return vals

    def get_registers_x64(self):
        log.debug('Getting registers')

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
        vals = dict(vals.items() + sse.items())

        # Get FPU registers
        fpu = self.get_registers_fpu()
        vals = dict(vals.items() + fpu.items())

        log.debug('Got registers: ' + str(vals))
        return vals

    def get_registers_sse(self, num=8):
        regs = {}
        for i in range(num):
            reg = 'xmm'+str(i)
            try:
                regs[reg] = int(str(gdb.parse_and_eval('$'+reg+'.uint128')), 16) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
            except:
                log.debug('Failed getting reg: ' + reg)
                regs[reg] = 'N/A'
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

    def get_register(self, reg):
        log.debug('Getting register: ' + reg)
        arch = self.get_arch()
        if arch == 'x64':
            return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF
        elif arch == 'x86':
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
        elif arch == 'arm':
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF

    def get_registers_arm(self):
        return {}

    def get_disasm(self):
        log.debug('Getting disasm')
        arch = self.get_arch()
        if arch == 'x64':
            ip = 'rip'
        elif arch == 'x86':
            ip = 'eip'
        elif arch == 'arm':
            ip = 'pc'
        res = gdb.execute('x/{}i ${}'.format(DISASM_MAX, ip), to_string=True)
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
        res = str(gdb.selected_inferior().read_memory(sp, STACK_MAX*16))
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

