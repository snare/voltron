import voltron
import logging
import base64

from voltron.api import *

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
    def __init__(self, target_id=0, count=None, address=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if count != None:
            self.count = count
        if target_id != None:
            self.target_id = target_id
        if address != None:
            self.address = address

    @server_side
    def dispatch(self):
        try:
            if self.address == None:
                self.address = self.debugger.read_program_counter(target_id=self.target_id)
            disasm = self.debugger.disassemble(target_id=self.target_id, address=self.address, count=self.count)
            res = APIDisassembleResponse()
            res.disassembly = disasm
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except Exception, e:
            msg = "Unhandled exception {} disassembling: {}".format(type(e), e)
            log.error(msg)
            res = APIErrorResponse(code=0, message=msg)

        return res

    def validate(self):
        if self.count == None:
            raise InvalidMessageException("Count missing")

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value

    @property
    def count(self):
        return self.data['count']

    @count.setter
    def count(self, value):
        self.data['count'] = value

    @property
    def address(self):
        return self.data['address']

    @address.setter
    def address(self, value):
        self.data['address'] = value


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
    @property
    def disassembly(self):
        return self.data['disassembly']

    @disassembly.setter
    def disassembly(self, value):
        self.data['disassembly'] = value


class APIDisassemblePlugin(APIPlugin):
    request = 'disassemble'
    request_class = APIDisassembleRequest
    response_class = APIDisassembleResponse
