import voltron
import logging

from voltron.api import *

log = logging.getLogger('api')


class APIReadRegistersRequest(APIRequest):
    """
    API state request.

    {
        "type":         "request",
        "request":      "read_registers",
        "data": {
            "target_id": 0,
            "thread_id": 123456
        }
    }

    `target_id` and `thread_id` are optional. If not present, the currently
    selected target and thread will be used.

    This request will return immediately.
    """
    def __init__(self, target_id=0, thread_id=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if target_id != None:
            self.target_id = target_id
        if thread_id != None:
            self.thread_id = thread_id

    @server_side
    def dispatch(self):
        try:
            regs = self.debugger.read_registers(target_id=self.target_id, thread_id=self.thread_id)
            res = APIReadRegistersResponse()
            res.registers = regs
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception, e:
            msg = "Exception getting registers from debugger: {}".format(e)
            log.error(msg)
            res = APIGenericErrorResponse()
            res.error_message = msg

        return res

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value

    @property
    def thread_id(self):
        return self.data['thread_id']

    @thread_id.setter
    def thread_id(self, value):
        self.data['thread_id'] = value


class APIReadRegistersResponse(APISuccessResponse):
    """
    API status response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "target":   "stopped"
        }
    }
    """
    @property
    def registers(self):
        return self.data['registers']

    @registers.setter
    def registers(self, value):
        self.data['registers'] = value



class APIReadRegistersPlugin(APIPlugin):
    request = 'read_registers'
    request_class = APIReadRegistersRequest
    response_class = APIReadRegistersResponse
