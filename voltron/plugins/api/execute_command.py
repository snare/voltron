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
    def __init__(self, command=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if command != None:
            self.command = command

    @server_side
    def dispatch(self):
        try:
            output = self.debugger.execute_command(self.command)
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

    @property
    def command(self):
        return self.data['command']

    @command.setter
    def command(self, value):
        self.data['command'] = value


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
    @property
    def output(self):
        return self.data['output']

    @output.setter
    def output(self, value):
        self.data['output'] = value


class APIExecuteCommandPlugin(APIPlugin):
    request = "execute_command"
    request_class = APIExecuteCommandRequest
    response_class = APIExecuteCommandResponse
