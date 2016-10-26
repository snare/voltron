import voltron
import logging
import six
import struct

from voltron.api import *

log = logging.getLogger('api')


class APIWriteMemoryRequest(APIRequest):
    """
    API write memory request.

    {
        "type":         "request",
        "request":      "write_memory",
        "data": {
            "target_id":0,
            "address":  0x12341234,
            "data":     "\xcc"
        }
    }

    `target_id` is optional. If not present, the currently selected target
    will be used.

    `address` is the address at which to start writing.

    `data` is the data to write.
    """
    _fields = {
        'target_id': False,
        'address': True,
        'value': True
    }
    _encode_fields = ['value']

    target_id = 0

    @server_side
    def dispatch(self):
        try:
            target = voltron.debugger.target(self.target_id)

            voltron.debugger.write_memory(address=int(self.address), data=self.value, target_id=int(self.target_id))

            res = APISuccessResponse()
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception writing memory in debugger: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APIWriteMemoryPlugin(APIPlugin):
    request = 'write_memory'
    request_class = APIWriteMemoryRequest
    response_class = APISuccessResponse
