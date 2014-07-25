import threading
import time
import logging

import voltron
from voltron.api import *

log = logging.getLogger('api')

class APIWaitRequest(APIRequest):
    """
    API wait request.

    {
        "type":         "request",
        "request":      "wait",
        "data": {
            "target_id":0
            "timeout":  10
            "state_changes": [
                "stopped"
            ],
        }
    }

    The server will wait until one of the specified state changes occurs or the
    timeout is reached before returning.

    The only supported state change currently is "stopped". Voltron console may
    implement some others.
    """
    _fields = {'target_id': False, 'timeout': False, 'state_changes': False}

    target_id = 0
    timeout = None
    state_changes = ['stopped']

    wait_event = None

    @server_side
    def dispatch(self):
        # tell the debugger adaptor that we want to know when state changes occur
        voltron.debugger.add_listener(self.update_state, self.state_changes)

        # wait until the flag is set by the debugger adapter callback telling us to check for a state change
        self.wait_event = threading.Event()
        timeout = int(self.timeout) if self.timeout != None else None
        log.debug("timeout = {}".format(timeout))
        flag = self.wait_event.wait(timeout)

        # remove the listener
        voltron.debugger.remove_listener(self.update_state)

        # if the wait timed out, return a timeout, otherwise return the wait response
        if not flag:
            res = APITimedOutErrorResponse()
        else:
            res = APIWaitResponse()
            res.state = voltron.debugger.state(self.target_id)

        return res

    def update_state(self):
        self.wait_event.set()


class APIWaitResponse(APISuccessResponse):
    """
    API wait response.

    {
        "type":         "response",
        "data": {
            "state":    "stopped"
        }
    }
    """
    _fields = {'state': True}

    state = None


class APIWaitPlugin(APIPlugin):
    request = 'wait'
    request_class = APIWaitRequest
    response_class = APIWaitResponse

