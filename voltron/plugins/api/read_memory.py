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
    def __init__(self, target_id=0, address=None, length=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if address != None:
            self.address = address
        if length != None:
            self.length = length
        if target_id != None:
            self.target_id = target_id

    @server_side
    def dispatch(self):
        try:
            memory = self.debugger.read_memory(address=self.address, length=self.length, target_id=self.target_id)
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

    @property
    def address(self):
        return self.data['address']

    @address.setter
    def address(self, value):
        self.data['address'] = int(value)

    @property
    def length(self):
        return self.data['length']

    @length.setter
    def length(self, value):
        self.data['length'] = int(value)

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value



class APIReadMemoryResponse(APISuccessResponse):
    """
    API read memory response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "memory":   "\xff..."
        }
    }
    """
    @property
    def memory(self):
        if self.data['memory']:
            return base64.b64decode(self.data['memory'])
        else:
            return None

    @memory.setter
    def memory(self, value):
        if value:
            self.data['memory'] = base64.b64encode(value)



class APIReadMemoryPlugin(APIPlugin):
    request = 'read_memory'
    request_class = APIReadMemoryRequest
    response_class = APIReadMemoryResponse
