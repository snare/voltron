import voltron
import logging
import base64

from voltron.api import *

log = logging.getLogger('api')

class APIStackRequest(APIRequest):
    """
    API read stack request.

    {
        "type":         "request",
        "request":      "stack"
        "data": {
            "target_id":    0,
            "thread_id":    123456,
            "length":       0x40
        }
    }

    `target_id` and `thread_id` are optional. If not present, the currently
    selected target and thread will be used.

    `length` is the number of bytes to read.
    """
    _fields = {'target_id': False, 'thread_id': False, 'length': True}

    target_id = 0
    thread_id = None
    length = None

    @server_side
    def dispatch(self):
        try:
            sp_name, sp = voltron.debugger.stack_pointer(target_id=self.target_id)
            memory = voltron.debugger.stack(self.length, target_id=self.target_id)
            res = APIStackResponse()
            res.memory = memory
            res.stack_pointer = sp
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except Exception as e:
            msg = "Unhandled exception {} reading stack: {}".format(type(e), e)
            log.exception(msg)
            res = APIErrorResponse(code=0, message=msg)

        return res


class APIStackResponse(APISuccessResponse):
    """
    API read stack response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "memory":           "\xff...",
            "stack_pointer":    0x12341234
        }
    }
    """
    _fields = {'memory': True, 'stack_pointer': True}

    _encode_fields = ['memory']

    memory = None
    stack_pointer = None


class APIStackPlugin(APIPlugin):
    request = 'stack'
    request_class = APIStackRequest
    response_class = APIStackResponse
