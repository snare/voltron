import voltron
from voltron.api import *


import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')


class APIBacktraceRequest(APIRequest):
    """
    API backtrace request.

    {
        "type":         "request",
        "request":      "backtrace"
    }
    """
    @server_side
    def dispatch(self):
        try:
            bt = voltron.debugger.backtrace()
            res = APIBacktraceResponse(frames=bt)
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting backtrace: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APIBacktraceResponse(APISuccessResponse):
    """
    API backtrace response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "frames": [
                {
                    "index": 0,
                    "addr": 0xffff,
                    "name": "inferior`main + 0"
                }
            ]
        }
    }
    """
    _fields = {'frames': True}

    frames = []


class APIBacktracePlugin(APIPlugin):
    request = "backtrace"
    request_class = APIBacktraceRequest
    response_class = APIBacktraceResponse
