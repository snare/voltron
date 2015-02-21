import voltron
import logging
import base64

from voltron.api import *

log = logging.getLogger('api')


class APIMemoryRequest(APIRequest):
    """
    API read memory request.

    {
        "type":         "request",
        "request":      "memory",
        "data": {
            "target_id":0,
            "address":  0x12341234,
            "length":   0x40
        }
    }

    `target_id` is optional. If not present, the currently selected target
    will be used.

    `address` is the address at which to start reading.

    `length` is the number of bytes to read.

    This request will return immediately.
    """
    _fields = {'target_id': False, 'address': True, 'length': True}

    target_id = 0
    address = None
    length = None

    @server_side
    def dispatch(self):
        try:
            memory = voltron.debugger.memory(address=self.address, length=self.length, target_id=self.target_id)
            res = APIMemoryResponse()
            res.memory = memory
            res.bytes = len(memory)
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting memory from debugger: {}".format(e)
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APIMemoryResponse(APISuccessResponse):
    """
    API read memory response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "memory":   "ABCDEF" # base64 encoded memory
        }
    }
    """
    _fields = {'memory': True, 'bytes': True}
    _encode_fields = ['memory']

    memory = None
    bytes = None


class APIReadMemoryPlugin(APIPlugin):
    request = 'memory'
    request_class = APIMemoryRequest
    response_class = APIMemoryResponse
