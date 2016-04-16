import logging
import importlib
try:
    from pygments.lexers import get_lexer_by_name
except:
    get_lexer_by_name = None

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger('view')


class CommandView (TerminalView):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('command', aliases=('c', 'cmd'),
                                   help='run a command each time the debugger host stops')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('command', action='store', help='command to run')
        sp.add_argument('--lexer', '-l', action='store',
                        help='apply a Pygments lexer to the command output (e.g. "c")',
                        default=None)
        sp.set_defaults(func=CommandView)

    def render(self):
        # Set up header and error message if applicable
        self.title = '[cmd:' + self.args.command + ']'

        # Get the command output
        res = self.client.perform_request('command', block=self.block, command=self.args.command)

        # don't render if it timed out, probably haven't stepped the debugger again
        if res.timed_out:
            return

        if res and res.is_success:
            if get_lexer_by_name and self.args.lexer:
                try:
                    lexer = get_lexer_by_name(self.args.lexer, stripall=True)
                    self.body = pygments.highlight(res.output, lexer, pygments.formatters.TerminalFormatter())
                except Exception as e:
                    log.warning('Failed to highlight view contents: ' + repr(e))
                    self.body = res.output
            else:
                self.body = res.output
        else:
            log.error("Error executing command: {}".format(res.message))
            self.body = self.colour(res.message, 'red')

        # Call parent's render method
        super(CommandView, self).render()


class CommandViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'command'
    view_class = CommandView
