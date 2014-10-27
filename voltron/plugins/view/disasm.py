from voltron.view import *
from voltron.plugin import *
from voltron.api import *


class DisasmView (TerminalView):
    view_type = 'disasm'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('disasm', help='disassembly view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=DisasmView)

    def render(self, error=None):
        height, width = self.window_size()

        # Set up header & error message if applicable
        self.title = '[code]'
        if error != None:
            self.body = self.colour(error, 'red')
        else:
            # Request data
            req = api_request('disassemble')
            req.count = self.body_height()
            res = self.client.send_request(req)
            if res.is_success:
                # Get the disasm
                disasm = res.disassembly
                disasm = '\n'.join(disasm.split('\n')[:self.body_height()])

                # Pygmentize output
                if have_pygments:
                    try:
                        lexer = pygments.lexers.get_lexer_by_name('gdb')
                        disasm = pygments.highlight(disasm, lexer, pygments.formatters.Terminal256Formatter())
                    except Exception as e:
                        log.warning('Failed to highlight disasm: ' + str(e))

                # Build output
                self.body = disasm.rstrip()
            else:
                log.error("Error disassembling: {}".format(res.message))
                self.body = self.colour(res.message, 'red')

        self.truncate_body()
        self.pad_body()

        # Call parent's render method
        super(DisasmView, self).render()


class DisasmViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'disassemble'
    view_class = DisasmView
