"""
Example command plugin

Copy this to your ~/.voltron/plugins directory. It will be loaded when
Voltron is initialised, and register a debugger command that works as follows:

$ lldb /tmp/inferior
Voltron loaded.
Run `voltron init` after you load a target.
(lldb) target create "/tmp/inferior"
Current executable set to '/tmp/inferior' (x86_64).
(lldb) b main
Breakpoint 1: where = inferior`main, address = 0x0000000100000cf0
(lldb) run
Process 12561 launched: '/tmp/inferior' (x86_64)
Process 12561 stopped
* thread #1: tid = 0x1d33f, 0x0000000100000cf0 inferior`main, queue = 'com.apple.main-thread', stop reason = breakpoint 1.1
    frame #0: 0x0000000100000cf0 inferior`main
inferior`main:
-> 0x100000cf0:  push   rbp
   0x100000cf1:  mov    rbp, rsp
   0x100000cf4:  sub    rsp, 0x50
   0x100000cf8:  mov    dword ptr [rbp - 0x4], 0x0
(lldb) example
rax 0000000100000CF0
rbx 0000000000000000
rcx 00007FFF5FBFFA70
rdx 00007FFF5FBFF978
rbp 00007FFF5FBFF958
rsp 00007FFF5FBFF948
rdi 0000000000000001
rsi 00007FFF5FBFF968
rip 0000000100000CF0
r8  0000000000000000
r9  00007FFF5FBFEA08
r10 0000000000000032
r11 0000000000000246
r12 0000000000000000
r13 0000000000000000
r14 0000000000000000
r15 0000000000000000
"""

import blessed
import voltron
from voltron.plugin import CommandPlugin
from voltron.command import VoltronCommand


class ExampleCommand(VoltronCommand):
    def invoke(self, *args):
        regs = voltron.debugger.registers()
        reg_list =  ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                     'r8','r9','r10','r11','r12','r13','r14','r15']
        for name in reg_list:
            print("{t.bold}{:3} {t.normal}{:0=16X}".format(name, regs[name], t=blessed.Terminal()))


class ExampleCommandPlugin(CommandPlugin):
    name = 'example'
    command_class = ExampleCommand