import logging

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
            # Get the command output
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
