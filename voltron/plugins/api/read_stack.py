import voltron
import logging
import base64

from voltron.api import *

log = logging.getLogger('api')

class APIReadStackRequest(APIRequest):
    """
    API read stack request.

    {
        "type":         "request",
        "request":      "read_stack"
        "data": {
            "target_id":    0,
            "thread_id":    123456,
            "length":       0x40
        }
    }

    `target_id` and `thread_id` are optional. If not present, the currently
    selected target and thread will be used.

    `length` is the number of bytes to read.

    This request will return immediately.
    """
    def __init__(self, length=None, target_id=0, thread_id=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if length != None:
            self.length = length
        if target_id != None:
            self.target_id = target_id
        if thread_id != None:
            self.thread_id = thread_id

    @server_side
    def dispatch(self):
        try:
            sp = self.debugger.read_stack_pointer(target_id=self.target_id)
            memory = self.debugger.read_stack(length=self.length, target_id=self.target_id)
            res = APIReadStackResponse()
            res.memory = memory
            res.stack_pointer = sp
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except TargetBusyException:
            res = APITargetBusyErrorResponse()
        except Exception, e:
            msg = "Unhandled exception {} reading stack: {}".format(type(e), e)
            log.error(msg)
            res = APIErrorResponse(code=0, message=msg)

        return res

    def validate(self):
        if self.length == None:
            raise InvalidMessageException("Length missing")

    @property
    def target_id(self):
        return self.data['target_id']

    @target_id.setter
    def target_id(self, value):
        self.data['target_id'] = value

    @property
    def thread_id(self):
        return self.data['thread_id']

    @thread_id.setter
    def thread_id(self, value):
        self.data['thread_id'] = value

    @property
    def length(self):
        return self.data['length']

    @length.setter
    def length(self, value):
        self.data['length'] = int(value)


class APIReadStackResponse(APISuccessResponse):
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

    @property
    def stack_pointer(self):
        return self.data['stack_pointer']

    @stack_pointer.setter
    def stack_pointer(self, value):
        self.data['stack_pointer'] = value



class APIReadStackPlugin(APIPlugin):
    request = 'read_stack'
    request_class = APIReadStackRequest
    response_class = APIReadStackResponse
