import voltron
import logging

from voltron.api import *

log = logging.getLogger('api')


class APIRegistersRequest(APIRequest):
    """
    API state request.

    {
        "type":         "request",
        "request":      "registers",
        "data": {
            "target_id": 0,
            "thread_id": 123456,
            "registers": ['rsp']
        }
    }

    `target_id` and `thread_id` are optional. If not present, the currently
    selected target and thread will be used.

    `registers` is optional. If it is not included all registers will be
    returned.
    """
    _fields = {'target_id': False, 'thread_id': False, 'registers': False}

    target_id = 0
    thread_id = None
    registers = []

    @server_side
    def dispatch(self):
        try:
            regs = voltron.debugger.registers(target_id=self.target_id, thread_id=self.thread_id, registers=self.registers)
            res = APIRegistersResponse()
            res.registers = regs
            res.deref = {}
            for reg, val in regs.items():
                try:
                    if val > 0:
                        try:
                            res.deref[reg] = voltron.debugger.dereference(pointer=val)
                        except:
                            res.deref[reg] = []
                    else:
                        res.deref[reg] = []
                except TypeError:
                    res.deref[reg] = []
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting registers from debugger: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APIRegistersResponse(APISuccessResponse):
    """
    API status response.

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "registers": { "rip": 0x12341234, ... },
            "deref": {"rip": [(pointer, 0x12341234), ...]}
        }
    }
    """
    _fields = {'registers': True, 'deref': False}


class APIRegistersPlugin(APIPlugin):
    request = 'registers'
    request_class = APIRegistersRequest
    response_class = APIRegistersResponse
