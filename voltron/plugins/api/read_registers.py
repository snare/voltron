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
    _fields = {'target_id': False, 'thread_id': False}

    target_id = 0
    thread_id = None

    @server_side
    def dispatch(self):
        try:
            regs = voltron.debugger.read_registers(target_id=self.target_id, thread_id=self.thread_id)
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


class APIReadRegistersResponse(APISuccessResponse):
    """
    API status response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "registers": { "rip": 0x12341234, ... }
        }
    }
    """
    _fields = {'registers': True}


class APIReadRegistersPlugin(APIPlugin):
    request = 'read_registers'
    request_class = APIReadRegistersRequest
    response_class = APIReadRegistersResponse
