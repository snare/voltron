import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')

class APIExecuteCommandRequest(APIRequest):
    """
    API execute command request.

    {
        "type":         "request",
        "request":      "execute_command"
        "data": {
            "command":  "break list"
        }
    }
    """
    _fields = {'command': True}

    @server_side
    def dispatch(self):
        try:
            output = voltron.debugger.execute_command(self.command)
            res = APIExecuteCommandResponse()
            res.output = output
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception, e:
            msg = "Exception executing debugger command: {}".format(e)
            log.error(msg)
            res = APIGenericErrorResponse()
            res.error_message = msg

        return res


class APIExecuteCommandResponse(APISuccessResponse):
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


class APIExecuteCommandPlugin(APIPlugin):
    request = "execute_command"
    request_class = APIExecuteCommandRequest
    response_class = APIExecuteCommandResponse
