import voltron
import logging
import base64

from voltron.api import *

log = logging.getLogger('api')


class APIReadMemoryRequest(APIRequest):
    """
    API read memory request.

    {
        "type":         "request",
        "request":      "read_memory",
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

    request = 'read_memory'

    target_id = 0
    address = None
    length = None

    @server_side
    def dispatch(self):
        try:
            memory = voltron.debugger.read_memory(address=self.address, length=self.length, target_id=self.target_id)
            res = APIReadMemoryResponse()
            res.memory = memory
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception, e:
            msg = "Exception getting memory from debugger: {}".format(e)
            log.error(msg)
            res = APIGenericErrorResponse()
            res.error_message = msg

        return res


class APIReadMemoryResponse(APISuccessResponse):
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
    _fields = {'memory': True}
    _encode_fields = ['memory']

    request = 'read_memory'

    memory = None


class APIReadMemoryPlugin(APIPlugin):
    request = 'read_memory'
    request_class = APIReadMemoryRequest
    response_class = APIReadMemoryResponse
