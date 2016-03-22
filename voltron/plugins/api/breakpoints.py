import voltron
from voltron.api import *


import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')


class APIBreakpointsRequest(APIRequest):
    """
    API breakpoints request.

    {
        "type":         "request",
        "request":      "breakpoints"
    }
    """
    @server_side
    def dispatch(self):
        try:
            bps = voltron.debugger.breakpoints()
            res = APIBreakpointsResponse(breakpoints=bps)
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting breakpoints: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APIBreakpointsResponse(APISuccessResponse):
    """
    API breakpoints response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "breakpoints": [
                {
                    "id":           1,
                    "enabled":      True,
                    "one_shot":     False,
                    "hit_count":    5,
                    "locations": [
                        {
                            "address":  0x100000cf0,
                            "name":     'main'
                        }
                    ]
                }
            ]
        }
    }
    """
    _fields = {'breakpoints': True}

    breakpoints = []


class APIBreakpointsPlugin(APIPlugin):
    request = "breakpoints"
    request_class = APIBreakpointsRequest
    response_class = APIBreakpointsResponse
