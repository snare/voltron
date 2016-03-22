import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')

class APITargetsRequest(APIRequest):
    """
    API list targets request.

    {
        "type":         "request",
        "request":      "targets"
    }
    """
    _fields = {}

    @server_side
    def dispatch(self):
        try:
            res = APITargetsResponse()
            res.targets = voltron.debugger.targets()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting targets from debugger: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APITargetsResponse(APISuccessResponse):
    """
    API list targets response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "targets": [{
                "id":       0,         # ID that can be used in other funcs
                "file":     "/bin/ls", # target's binary file
                "arch":     "x86_64",  # target's architecture
                "state:     "stopped"  # state
            }]
        }
    }
    """
    _fields = {'targets': True}

    targets = []


class APITargetsPlugin(APIPlugin):
    request = 'targets'
    request_class = APITargetsRequest
    response_class = APITargetsResponse

