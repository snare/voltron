import voltron
import logging

from voltron.api import *

log = logging.getLogger('api')

class APIStateRequest(APIRequest):
    """
    API state request.

    {
        "type":         "request",
        "request":      "state",
        "data": {
            "target_id": 0
        }
    }
    """
    _fields = {'target_id': False}

    target_id = 0

    @server_side
    def dispatch(self):
        try:
            state = voltron.debugger.state(target_id=self.target_id)
            log.debug("Got state from debugger: {}".format(state))
            res = APIStateResponse()
            res.state = state
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()

        return res


class APIStateResponse(APISuccessResponse):
    """
    API status response.

    {
        "type":         "response",
        "data": {
            "state":    "stopped"
        }
    }
    """
    _fields = {'state': True}

    state = None


class APIStatePlugin(APIPlugin):
    request = 'state'
    request_class = APIStateRequest
    response_class = APIStateResponse
