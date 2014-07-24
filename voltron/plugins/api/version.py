import voltron
import voltron.api
from voltron.api import *

from scruffy.plugin import Plugin


class APIVersionRequest(APIRequest):
    """
    API version request.

    {
        "type":         "request",
        "request":      "version"
    }
    """
    @server_side
    def dispatch(self):
        res = APIVersionResponse()
        res.api_version = voltron.api.version
        res.host_version = self.debugger.version()
        return res


class APIVersionResponse(APISuccessResponse):
    """
    API version response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "api_version":  1.0,
            "host_version": 'lldb-something'
        }
    }
    """
    @property
    def api_version(self):
        return self.data['api_version']

    @api_version.setter
    def api_version(self, value):
        self.data['api_version'] = float(value)

    @property
    def host_version(self):
        return self.data['host_version']

    @host_version.setter
    def host_version(self, value):
        self.data['host_version'] = str(value)



class APIVersionPlugin(APIPlugin):
    request = 'version'
    request_class = APIVersionRequest
    response_class = APIVersionResponse

