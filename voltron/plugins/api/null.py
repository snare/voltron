import voltron
import voltron.api
from voltron.api import *

from scruffy.plugin import Plugin


class APINullRequest(APIRequest):
    """
    API null request.

    {
        "type":         "request",
        "request":      "null"
    }
    """
    @server_side
    def dispatch(self):
        return APINullResponse()


class APINullResponse(APISuccessResponse):
    """
    API null response.

    {
        "type":         "response",
        "status":       "success"
    }
    """


class APINullPlugin(APIPlugin):
    request = 'null'
    request_class = APINullRequest
    response_class = APINullResponse
