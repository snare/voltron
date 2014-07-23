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
    def __init__(self, target_id=0, state_changes=None, timeout=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if target_id != None:
            self.target_id = target_id
        if timeout != None:
            self.timeout = timeout
        if state_changes != None:
            self.state_changes = state_changes
        self.wait_event = threading.Event()

    @server_side
    def dispatch(self):
        # make sure we have some state changes
        self.state_changes = self.state_changes if self.state_changes else ["stopped"]

        # tell the debugger adaptor that we want to know when state changes occur
        self.debugger.add_listener(self.update_state, self.state_changes)

        # wait until the flag is set by the debugger adapter callback telling us to check for a state change
        self.wait_event.clear()
        flag = self.wait_event.wait(self.timeout)

        # remove the listener
        self.debugger.remove_listener(self.update_state)

        # if the wait timed out, return a timeout, otherwise return the wait response
        if not flag:
            res = APITimedOutErrorResponse()
        else:
            res = APIWaitResponse()
            res.state = self.debugger.state(self.target_id)

        return res

    def update_state(self):
        self.wait_event.set()

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value

    @property
    def state_changes(self):
        return self.data['state_changes']

    @state_changes.setter
    def state_changes(self, value):
        self.data['state_changes'] = value

    @property
    def timeout(self):
        return self.data['timeout']

    @timeout.setter
    def timeout(self, value):
        self.data['timeout'] = value


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
    @property
    def state(self):
        return self.data['state']

    @state.setter
    def state(self, value):
        self.data['state'] = value



class APIWaitPlugin(APIPlugin):
    request = 'wait'
    request_class = APIWaitRequest
    response_class = APIWaitResponse

