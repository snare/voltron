"""
Example Voltron view.

Copy this to your ~/.voltron/plugins directory. When the `voltron view` command
is executed, 'example' should be visible in the list of valid view names.

Start your debugger as follows:

$ lldb /tmp/inferior
Voltron loaded.
Run `voltron init` after you load a target.
(lldb) target create "/tmp/inferior"
Current executable set to '/tmp/inferior' (x86_64).
(lldb) voltron init
Registered stop-hook
(lldb) b main
Breakpoint 1: where = inferior`main, address = 0x0000000100000cf0
(lldb) run
Process 13185 launched: '/Volumes/Data/Users/snare/code/voltron/repo/tests/inferior' (x86_64)
Process 13185 stopped
* thread #1: tid = 0x1ee63, 0x0000000100000cf0 inferior`main, queue = 'com.apple.main-thread', stop reason = breakpoint 1.1
    frame #0: 0x0000000100000cf0 inferior`main
inferior`main:
-> 0x100000cf0:  push   rbp
   0x100000cf1:  mov    rbp, rsp
   0x100000cf4:  sub    rsp, 0x50
   0x100000cf8:  mov    dword ptr [rbp - 0x4], 0x0

Run this view in another terminal (as follows). Each time you `stepi` in the
debugger, the view will update and display the current register values.

$ voltron view example
"""

from voltron.view import TerminalView
from voltron.plugin import ViewPlugin


class ExampleView(TerminalView):
    def render(self, *args, **kwargs):
        # Perform the request
        res = self.client.perform_request('registers')
        if res.is_success:
            # Process the registers and set the body to the formatted list
            reg_list =  ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                         'r8','r9','r10','r11','r12','r13','r14','r15']
            lines = map(lambda x: '{:3}: {:016X}'.format(x, res.registers[x]), reg_list)
            self.body = '\n'.join(lines)
        else:
            self.body = "Failed to get registers: {}".format(res)

        # Set the title and info
        self.title = '[example]'
        self.info = 'some infoz'

        # Let the parent do the rendering
        super(ExampleView, self).render()


class ExampleViewPlugin(ViewPlugin):
    name = 'example'
    view_class = ExampleView
