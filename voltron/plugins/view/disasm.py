from voltron.view import *
from voltron.plugin import *
from voltron.api import *
try:
    from voltron.lexers import *
    have_pygments = True
except ImportError:
    have_pygments = False


class DisasmView(TerminalView):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('disasm', help='disassembly view', aliases=('d', 'dis', 'disasm'))
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=DisasmView)
        sp.add_argument('--use-capstone', '-c', action='store_true', default=False, help='use capstone')

    def render(self):
        height, width = self.window_size()

        # Set up header & error message if applicable
        self.title = '[disassembly]'

        # Request data
        req = api_request('disassemble', block=self.block, use_capstone=self.args.use_capstone)
        req.count = self.body_height()
        res = self.client.send_request(req)

        # don't render if it timed out, probably haven't stepped the debugger again
        if res.timed_out:
            return

        if res and res.is_success:
            # Get the disasm
            disasm = res.disassembly
            disasm = '\n'.join(disasm.split('\n')[:self.body_height()])

            # Pygmentize output
            if have_pygments:
                try:
                    host = 'capstone' if self.args.use_capstone else res.host
                    lexer = all_lexers['{}_{}'.format(host, res.flavor)]()
                    disasm = pygments.highlight(disasm, lexer, pygments.formatters.TerminalFormatter())
                except Exception as e:
                    log.warning('Failed to highlight disasm: ' + str(e))

            # Build output
            self.body = disasm.rstrip()
        else:
            log.error("Error disassembling: {}".format(res.message))
            self.body = self.colour(res.message, 'red')

        # Call parent's render method
        super(DisasmView, self).render()


class DisasmViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'disassembly'
    aliases = ('d', 'dis', 'disasm')
    view_class = DisasmView
