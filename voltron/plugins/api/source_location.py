import logging

import voltron
from voltron.api import *

from scruffy.plugin import Plugin

log = logging.getLogger('api')

class APISourceLocationRequest(APIRequest):
    """
    API source location from address request.

    {
        "type":         "request",
        "request":      "source_location"
        "data": {
            "target_id": 0,
            "address":  0xffffff8012341234
        }
    }
    `target_id` is optional.
    `address` is the address to lookup source information for. Defaults to
    instruction pointer if not specified.
    """
    _fields = {'target_id': False, 'address': False}

    @server_side
    def dispatch(self):
        try:
            output = voltron.debugger.source_location(target_id=self.target_id, address=self.address)
            log.debug('output: {}'.format(str(output)))
            res = APISourceLocationResponse()
            res.output = output
        except NoSuchTargetException:
            res = APINoSuchTargetErrorResponse()
        except Exception as e:
            msg = "Exception finding source location from address: {}".format(repr(e))
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class APISourceLocationResponse(APISuccessResponse):
    """
    API source location from address response. Output may be None if no
    sorce information is available for the address

    {
        "type":         "response",
        "status":       "success",
        "data": {
            "output":   ["main.c", 8]
        }
    }
    """
    _fields = {'output': True}

    output = None


class APISourceLocationPlugin(APIPlugin):
    request = "source_location"
    request_class = APISourceLocationRequest
    response_class = APISourceLocationResponse
