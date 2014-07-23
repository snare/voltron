from __future__ import print_function

import os
import sys
import logging
import re

from voltron.api import *

log = logging.getLogger(__name__)

try:
    import gdb
    HAVE_GDB = True
except:
    HAVE_GDB = False

if HAVE_GDB:

    class VoltronGDBCommand (VoltronCommand, gdb.Command):
        def __init__(self):
            super(VoltronCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)
            self.running = False
            self.server = None
            self.helper = None
            self.base_helper = GDBHelper

        def invoke(self, arg, from_tty):
            self.handle_command(arg)

        def register_hooks(self):
            gdb.events.stop.connect(self.stop_handler)
            gdb.events.exited.connect(self.exit_handler)
            gdb.events.cont.connect(self.cont_handler)

        def unregister_hooks(self):
            gdb.events.stop.disconnect(self.stop_handler)
            gdb.events.exited.disconnect(self.exit_handler)
            gdb.events.cont.disconnect(self.cont_handler)

        def stop_handler(self, event):
            log.debug('Inferior stopped')
            self.update()

        def exit_handler(self, event):
            log.debug('Inferior exited')
            self.stop_server()
            self.helper = None

        def cont_handler(self, event):
            log.debug('Inferior continued')
            if self.server == None:
                self.start_server()


    class GDBHelper (DebuggerHelper):
        @staticmethod
        def has_target():
            return len(gdb.inferiors()) > 0

        @staticmethod
        def get_arch():
            try:
                return gdb.selected_frame().architecture().name()
            except:
                return re.search('\(currently (.*)\)', gdb.execute('show architecture', to_string=True)).group(1)

        @staticmethod
        def helper():
            arch = GDBHelper.get_arch()
            for cls in GDBHelper.__subclasses__():
                if hasattr(cls, 'archs') and arch in cls.archs:
                    return cls()
            raise LookupError('No helper found for arch {}'.format(arch))

        def get_next_instruction(self):
            return self.get_disasm().split('\n')[0].split(':')[1].strip()

        def get_disasm(self):
            log.debug('Getting disasm')
            res = gdb.execute('x/{}i ${}'.format(DISASM_MAX, self.get_pc_name()), to_string=True)
            return res

        def get_stack(self):
            log.debug('Getting stack')
            res = str(gdb.selected_inferior().read_memory(self.get_sp(), STACK_MAX*16))
            return res

        def get_memory(self, start, length):
            log.debug('Getting %x + %d' % (start, length))
            res = str(gdb.selected_inferior().read_memory(start, length))
            return res

        def get_backtrace(self):
            log.debug('Getting backtrace')
            res = gdb.execute('bt', to_string=True)
            return res

        def get_cmd_output(self, cmd=''):
            log.debug('Getting command output: ' + cmd)
            res = gdb.execute(cmd, to_string=True)
            return res


    class GDBHelperX86 (GDBHelper):
        archs = ['i386', 'i386:intel', 'i386:x64-32', 'i386:x64-32:intel', 'i8086']
        arch_group = 'x86'
        pc = 'eip'
        sp = 'esp'

        def get_registers(self):
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
            vals = dict(list(vals.items()) + list(sse.items()))

            # Get FPU registers
            fpu = self.get_registers_fpu()
            vals = dict(list(vals.items()) + list(fpu.items()))

            log.debug('Got registers: ' + str(vals))
            return vals

        def get_registers_sse(self, num=8):
            # the old way of doing this randomly crashed gdb or threw a python exception
            regs = {}
            for line in gdb.execute('info all-registers', to_string=True).split('\n'):
                m = re.match('^(xmm\d+)\s.*uint128 = (0x[0-9a-f]+)\}', line)
                if m:
                    regs[m.group(1)] = int(m.group(2), 16)
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
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF


    class GDBHelperX64 (GDBHelperX86, GDBHelper):
        archs = ['i386:x86-64', 'i386:x86-64:intel']
        arch_group = 'x64'
        pc = 'rip'
        sp = 'rsp'

        def get_registers(self):
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
            vals = dict(list(vals.items()) + list(sse.items()))

            # Get FPU registers
            fpu = self.get_registers_fpu()
            vals = dict(list(vals.items()) + list(fpu.items()))

            log.debug('Got registers: ' + str(vals))
            return vals

        def get_register(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF


    class GDBHelperARM (GDBHelper):
        archs = ['arm', 'arm', 'armv2', 'armv2a', 'armv3', 'armv3m', 'armv4', 'armv4t', 'armv5', 'armv5t', 'armv5te']
        arch_group = 'arm'
        pc = 'pc'
        sp = 'sp'

        def get_registers(self):
            log.debug('Getting registers')
            regs = ['pc','sp','lr','cpsr','r0','r1','r2','r3','r4','r5','r6', 'r7','r8','r9','r10','r11','r12']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'
            return vals

        def get_register(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long)$'+reg)) & 0xFFFFFFFF
