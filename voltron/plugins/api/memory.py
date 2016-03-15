import voltron
import logging
import base64
import six

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

    `register` is the register containing the address at which to start reading.

    `command` is the debugger command to execute to calculate the address at
    which to start reading.

    `deref` is a flag indicating whether or not to dereference any pointers
    within the memory region read.
    """
    _fields = {
        'target_id': False,
        'address': False,
        'length': False,
        'words': False,
        'register': False,
        'command': False,
        'deref': False
    }

    target_id = 0

    @server_side
    def dispatch(self):
        try:
            target = voltron.debugger.target(self.target_id)

            # if 'words' was specified, get the addr_size and calculate the length to read
            if self.words:
                self.length = self.words * target['addr_size']

            # calculate the address at which to begin reading
            if self.address:
                addr = self.address
            elif self.command:
                output = voltron.debugger.command(self.args.command)
                if output:
                    for item in reversed(output.split()):
                        log.debug("checking item: {}".format(item))
                        try:
                            addr = int(item)
                            break
                        except:
                            try:
                                addr = int(item, 16)
                                break
                            except:
                                pass
            elif self.register:
                regs = voltron.debugger.registers(registers=[self.register])
                addr = list(regs.values())[0]

            # read memory
            memory = voltron.debugger.memory(address=int(addr), length=int(self.length), target_id=int(self.target_id))

            # deref pointers
            deref = None
            if self.deref:
                fmt = ('<' if target['byte_order'] == 'little' else '>') + {2: 'H', 4: 'L', 8: 'Q'}[target['addr_size']]
                deref = []
                for chunk in zip(*[six.iterbytes(memory)] * target['addr_size']):
                    chunk = ''.join([six.unichr(x) for x in chunk]).encode('latin1')
                    p = list(struct.unpack(fmt, chunk))[0]
                    if p > 0:
                        try:
                            deref.append(voltron.debugger.dereference(pointer=p))
                        except:
                            deref.append([])
                    else:
                        deref.append([])

            res = APIMemoryResponse()
            res.address = addr
            res.memory = six.u(memory)
            res.bytes = len(memory)
            res.deref = deref
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception getting memory from debugger: {}".format(repr(e))
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
    _fields = {
        'address': True,
        'memory': True,
        'bytes': True,
        'deref': False
    }
    _encode_fields = ['memory']

    address = None
    memory = None
    bytes = None
    deref = None


class APIReadMemoryPlugin(APIPlugin):
    request = 'memory'
    request_class = APIMemoryRequest
    response_class = APIMemoryResponse
