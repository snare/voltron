import logging

from voltron.view import *
from voltron.plugin import ViewPlugin

log = logging.getLogger('view')


class BacktraceView (TerminalView):
    view_type = 'bt'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('bt', help='backtrace view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=BacktraceView)

    def render(self, msg=None, error=None):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = '[backtrace]'
        if error != None:
            self.body = self.colour(error, 'red')
        else:
            req = self.pm.api_plugin_for_request('execute_command').request_class()
            req.command = "bt"
            res = self.client.send_request(req)
            if res.is_success:
                # Get the command output
                self.body = res.output
            else:
                log.error("Error getting backtrace: {}".format(res.error_message))
                self.body = self.colour(res.error_message, 'red')

        # Pad body
        self.pad_body()

        # Call parent's render method
        super(BacktraceView, self).render()


class BacktraceViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'backtrace'
    view_class = BacktraceView
