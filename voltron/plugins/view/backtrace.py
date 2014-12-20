import logging

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger('view')


class BacktraceView (TerminalView):
    def render(self):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = '[backtrace]'
        req = api_request('command')
        req.command = "bt"
        res = self.client.send_request(req)
        if res.is_success:
            # Get the command output
            self.body = res.output
        else:
            log.error("Error getting backtrace: {}".format(res.message))
            self.body = self.colour(res.message, 'red')

        # Call parent's render method
        super(BacktraceView, self).render()


class BacktraceViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'backtrace'
    view_class = BacktraceView
