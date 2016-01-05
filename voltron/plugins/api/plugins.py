import voltron
import voltron.api
from voltron.api import *

from scruffy.plugin import Plugin


class APIPluginsRequest(APIRequest):
    """
    API plugins request.

    {
        "type":         "request",
        "request":      "plugins"
    }
    """
    @server_side
    def dispatch(self):
        res = APIPluginsResponse()
        return res


class APIPluginsResponse(APISuccessResponse):
    """
    API plugins response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "plugins": {
                "api": {
                    "version": ["api_version", "host_version", "capabilities"]
                    ...
                },
                "debugger": {
                    ...
                },
                ...
            }
        }
    }
    """
    _fields = {
        'plugins': True
    }

    def __init__(self, *args, **kwargs):
        super(APIPluginsResponse, self).__init__(*args, **kwargs)
        self.plugins = {
            'api': {n: {'request': p.request_class._fields, 'response': p.response_class._fields}
                    for (n, p) in voltron.plugin.pm.api_plugins.iteritems()},
            'debugger': [n for n in voltron.plugin.pm.debugger_plugins],
            'view': [n for n in voltron.plugin.pm.view_plugins],
            'command': [n for n in voltron.plugin.pm.command_plugins],
            'web': [n for n in voltron.plugin.pm.web_plugins],
        }


class APIPluginsPlugin(APIPlugin):
    request = 'plugins'
    request_class = APIPluginsRequest
    response_class = APIPluginsResponse
