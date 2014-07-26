import logging

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger("view")

class StackView (TerminalView):
    view_type = 'stack'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('stack', help='stack view')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.set_defaults(func=StackView)

    def render(self, error=None):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = "[stack]"
        if error != None:
            self.body = self.colour(error, 'red')
        else:
            # Request data
            req = api_request('read_stack')
            req.length = self.body_height()*self.args.bytes
            res = self.client.send_request(req)
            if res.is_success:
                # Get the stack data
                sp = res.stack_pointer
                stack_raw = res.memory

                # Hexdump it
                lines = self.hexdump(stack_raw, offset=sp, length=self.args.bytes).split('\n')
                lines.reverse()
                stack = '\n'.join(lines)

                # Build output
                self.info = '[0x{0:0=4x}:'.format(len(stack_raw)) + ADDR_FORMAT_64.format(sp) + ']'
                self.body = stack.strip()
            else:
                log.error("Error requesting stack: {}".format(res.message))
                self.body = self.colour(res.message, 'red')

        self.pad_body()

        # Call parent's render method
        super(StackView, self).render()


class StackViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'stack'
    view_class = StackView
