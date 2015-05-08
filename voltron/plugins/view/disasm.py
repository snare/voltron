from voltron.view import *
from voltron.plugin import *
from voltron.api import *
try:
    from voltron.lexers import *
    have_pygments = True
except ImportError:
    have_pygments = False

class DisasmView (TerminalView):
    def render(self):
        height, width = self.window_size()

        # Set up header & error message if applicable
        self.title = '[code]'

        # Request data
        req = api_request('disassemble')
        req.count = self.body_height()
        res = self.client.send_request(req)
        if res and res.is_success:
            # Get the disasm
            disasm = res.disassembly
            disasm = '\n'.join(disasm.split('\n')[:self.body_height()])

            # Pygmentize output
            if have_pygments:
                try:
                    lexer = all_lexers['{}_{}'.format(res.host, res.flavor)]()
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
