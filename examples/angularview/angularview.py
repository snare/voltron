import logging
import pygments
from voltron.plugin import *
from voltron.lexers import *
from voltron.api import *

from flask import *

log = logging.getLogger('api')


class AngularViewPlugin(WebPlugin):
    name = 'angularview'


class FormatDisassemblyRequest(APIRequest):
    _fields = {'disassembly': True}

    def dispatch(self):
        try:
            res = FormatDisassemblyResponse(
                disassembly=pygments.highlight(self.disassembly.strip(), LLDBIntelLexer(), pygments.formatters.HtmlFormatter()))
        except Exception as e:
            msg = "Exception formatting disassembly: {}".format(e)
            log.exception(msg)
            res = APIGenericErrorResponse(msg)

        return res


class FormatDisassemblyResponse(APIResponse):
    _fields = {'disassembly': True}


class FormatDisassemblyPlugin(APIPlugin):
    request = "format_disasm"
    request_class = FormatDisassemblyRequest
    response_class = FormatDisassemblyResponse
