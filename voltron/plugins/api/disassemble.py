import voltron
import logging

from voltron.api import *
from voltron.plugin import *

log = logging.getLogger('api')

class APIDisassembleRequest(APIRequest):
    """
    API disassemble request.

    {
        "type":         "request",
        "request":      "disassemble"
        "data": {
            "target_id":    0,
            "address":      0x12341234,
            "count":        16
        }
    }

    `target_id` is optional.
    `address` is the address at which to start disassembling. Defaults to
    instruction pointer if not specified.
    `count` is the number of instructions to disassemble.

    This request will return immediately.
    """
    _fields = {'target_id': False, 'address': False, 'count': True}

    target_id = 0
    address = None
    count = 16

    @server_side
    def dispatch(self):
        try:
            if self.address == None:
                pc_name, self.address = voltron.debugger.program_counter(target_id=self.target_id)
            disasm = voltron.debugger.disassemble(target_id=self.target_id, address=self.address, count=self.count)
            res = APIDisassembleResponse()
            res.disassembly = disasm
            try:
                res.flavor = voltron.debugger.disassembly_flavor()
            except:
                res.flavor = 'NA'
            res.host = voltron.debugger._plugin.host
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except Exception as e:
            msg = "Unhandled exception {} disassembling: {}".format(type(e), e)
            log.exception(msg)
            res = APIErrorResponse(code=0, message=msg)

        return res


class APIDisassembleResponse(APISuccessResponse):
    """
    API disassemble response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "disassembly":  "mov blah blah"
        }
    }
    """
    _fields = {'disassembly': True, 'formatted': False, 'flavor': False, 'host': False}

    disassembly = None
    formatted = None
    flavor = None
    host = None


class APIDisassemblePlugin(APIPlugin):
    request = 'disassemble'
    request_class = APIDisassembleRequest
    response_class = APIDisassembleResponse
