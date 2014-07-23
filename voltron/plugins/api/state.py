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

    This request will return immediately.
    """
    def __init__(self, target_id=0, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if target_id != None:
            self.target_id = target_id

    @server_side
    def dispatch(self):
        try:
            state = self.debugger.state(target_id=self.target_id)
            log.debug("Got state from debugger: {}".format(state))
            res = APIStateResponse()
            res.status = "success"
            res.state = state
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()

        return res

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value


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
    @property
    def state(self):
        return self.data['state']

    @state.setter
    def state(self, value):
        self.data['state'] = value


class APIStatePlugin(APIPlugin):
    request = 'state'
    request_class = APIStateRequest
    response_class = APIStateResponse
