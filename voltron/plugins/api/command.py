import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')

class APICommandRequest(APIRequest):
    """
    API execute command request.

    {
        "type":         "request",
        "request":      "command"
        "data": {
            "command":  "break list"
        }
    }
    """
    _fields = {'command': True}

    @server_side
    def dispatch(self):
        try:
            output = voltron.debugger.command(self.command)
            res = APICommandResponse()
            res.output = output
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception executing debugger command: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APICommandResponse(APISuccessResponse):
    """
    API list targets response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "output":   "stuff"
        }
    }
    """
    _fields = {'output': True}

    output = None


class APICommandPlugin(APIPlugin):
    request = "command"
    request_class = APICommandRequest
    response_class = APICommandResponse
