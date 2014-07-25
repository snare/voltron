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
        res.host_version = voltron.debugger.version()
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
    _fields = {'api_version': True, 'host_version': True}

    api_version = None
    host_version = None

class APIVersionPlugin(APIPlugin):
    request = 'version'
    request_class = APIVersionRequest
    response_class = APIVersionResponse

