import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')

class APIListTargetsRequest(APIRequest):
    """
    API list targets request.

    {
        "type":         "request",
        "request":      "list_targets"
    }
    """
    _fields = {}

    @server_side
    def dispatch(self):
        try:
            res = APIListTargetsResponse()
            res.targets = voltron.debugger.targets()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception, e:
            msg = "Exception getting targets from debugger: {}".format(e)
            log.error(msg)
            res = APIGenericErrorResponse()
            res.error_message = msg

        return res


class APIListTargetsResponse(APISuccessResponse):
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


class APIListTargetsPlugin(APIPlugin):
    request = 'list_targets'
    request_class = APIListTargetsRequest
    response_class = APIListTargetsResponse

