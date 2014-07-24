import os
import logging
import socket
import select
import threading
import logging
import logging.config
import json
import inspect

from collections import defaultdict

from scruffy.plugin import Plugin

import voltron
from .plugin import PluginManager, APIPlugin

log = logging.getLogger('api')

version = 1.0


class VoltronAPIException(Exception):
    """
    Generic Voltron API exception
    """
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return "<{} code={} message=\"{}\">".format(self.__class__.__name__, self.code, self.message)


class InvalidRequestTypeException(Exception):
    """
    Exception raised when the client is requested to send an invalid request type.
    """
    pass

class InvalidMessageException(Exception):
    """
    Exception raised when an invalid API message is received.
    """
    pass

class ServerSideOnlyException(Exception):
    """
    Exception raised when a server-side method is called on an APIMessage
    subclass that exists on the client-side.

    See @server_side decorator.
    """
    pass

class ClientSideOnlyException(Exception):
    """
    Exception raised when a server-side method is called on an APIMessage
    subclass that exists on the client-side.

    See @client_side decorator.
    """
    pass

class DebuggerNotPresentException(Exception):
    """
    Raised when an APIRequest is dispatched without a valid debugger present.
    """
    pass

class NoSuchTargetException(Exception):
    """
    Raised when an APIRequest specifies an invalid target.
    """
    pass

class TargetBusyException(Exception):
    """
    Raised when an APIRequest specifies a target that is currently busy and
    cannot be queried.
    """
    pass

def server_side(func):
    """
    Decorator to designate an API method applicable only to server-side
    instances.

    This allows us to use the same APIRequest and APIResponse subclasses on the
    client and server sides without too much confusion.
    """
    def inner(*args, **kwargs):
        if len(args) and hasattr(args[0], 'is_server'):
            if args[0].is_server == True:
                return func(*args, **kwargs)
            else:
                raise ServerSideOnlyException("This method can only be called on a server-side instance")
        else:
            return func(*args, **kwargs)
    return inner


def client_side(func):
    """
    Decorator to designate an API method applicable only to client-side
    instances.

    This allows us to use the same APIRequest and APIResponse subclasses on the
    client and server sides without too much confusion.
    """
    def inner(*args, **kwargs):
        if len(args) and hasattr(args[0], 'is_server'):
            if args[0].is_server == False:
                return func(*args, **kwargs)
            else:
                raise ClientSideOnlyException("This method can only be called on a client-side instance")
        else:
            return func(*args, **kwargs)
    return inner


class APIMessage(object):
    """
    Top-level API message class.
    """
    _type = None
    _plugin = None

    def __init__(self, data=None):
        """
        Top-level initialiser for all API messages.

        `data` is a string containing JSON data.
        """
        # initialise properties
        self.props = {}

        # set type
        self.type = self._type

        # process any data that was passed in
        if data:
            try:
                self.props = dict(self.props.items() + json.loads(data).items())
            except ValueError:
                raise InvalidMessageException("Invalid message")

    def __str__(self):
        """
        Return a string containing the API message properties in JSON format.
        """
        return json.dumps(self.props)

    @property
    def props(self):
        return self._props

    @props.setter
    def props(self, value):
        self._props = defaultdict(lambda: None, value)
        if self.data:
            self.data = self.data
        else:
            self.data = {}

    def validate(self):
        raise InvalidMessageException("Implement the validate method for your APIMessage subclass")

    @property
    def type(self):
        if 'type' in self.props:
            return self.props['type']
        return None

    @type.setter
    def type(self, value):
        self.props['type'] = value

    @property
    def data(self):
        if 'data' in self.props:
            return self.props['data']
        return None

    @data.setter
    def data(self, value):
        self.props['data'] = defaultdict(lambda: None, value)

    @property
    def has_data(self):
        return 'data' in self.props and self.data != None

    @property
    def plugin(self):
        return self._plugin

    @plugin.setter
    def plugin(self, value):
        self._plugin = value


class APIRequest(APIMessage):
    """
    An API request object. Contains functions and accessors common to all API
    request types.

    Subclasses of APIRequest are used on both the client and server sides. On
    the server side they are instantiated by APIDispatcher's `handle_request()`
    method. On the client side they are instantiated by whatever class is doing
    the requesting (probably a view class).
    """
    _type = "request"
    _debugger = None
    _request = None

    def __init__(self, data=None, debugger=None):
        # initialise the request with whatever data was passed
        super(APIRequest, self).__init__(data=data)

        # initialise the request type and plugin from the one provided by the plugin manager
        if not data:
            self.request = self._request
        self.plugin = self._plugin

        # keep a reference to the debugger
        if debugger:
            self.debugger = debugger

        # if we don't have a debugger yet, try the package-wide global
        if not self.debugger:
            self.debugger = voltron.debugger

    @server_side
    def dispatch(self):
        """
        In concrete subclasses this method will actually dispatch the request
        to the debugger host and return a response. In this case it raises an
        exception.
        """
        raise NotImplementedError("Subclass APIRequest")

    @property
    def request(self):
        if 'request' in self.props:
            return self.props['request']
        return None

    @request.setter
    def request(self, value):
        self.props['request'] = str(value)

    @property
    def debugger(self):
        return self._debugger

    @debugger.setter
    def debugger(self, value):
        self._debugger = value

    def validate(self):
        if not self.request:
            raise InvalidMessageException("No request type")


class APIResponse(APIMessage):
    """
    An API response object. Contains functions and accessors common to all API
    response types.

    Subclasses of APIResponse are used on both the client and server sides. On
    the server side they are instantiated by the APIRequest's `dispatch` method
    in order to serialise and send to the client. On the client side they are
    instantiated by the Client class and returned by `send_request`.
    """
    _type = "response"

    @property
    def status(self):
        return self.props['status']

    @status.setter
    def status(self, value):
        self.props['status'] = str(value)

    @property
    def is_success(self):
        return self.props['status'] == 'success'

    @property
    def is_error(self):
        return self.props['status'] == 'error'

    @property
    def error_code(self):
        if self.status == 'error' and 'code' in self.data:
            return self.data['code']
        return None

    @error_code.setter
    def error_code(self, value):
        self.data['code'] = int(value)

    @property
    def error_message(self):
        if self.status == 'error' and 'message' in self.data:
            return self.data['message']
        return None

    @error_message.setter
    def error_message(self, value):
        self.data['message'] = str(value)

    def validate(self):
        if not self.status:
            raise InvalidMessageException("No status")
        if self.is_error and (not self.error_code or not self.error_message):
            raise InvalidMessageException("Error status without full error report")


class APISuccessResponse(APIResponse):
    """
    A generic API success response.
    """
    def __init__(self, data=None):
        super(APIResponse, self).__init__(data=data)
        self.status = "success"


class APIErrorResponse(APIResponse):
    """
    A generic API error response.
    """
    def __init__(self, code=None, message=None, *args, **kwargs):
        super(APIErrorResponse, self).__init__(*args, **kwargs)
        self.status = "error"
        if hasattr(self.__class__, 'code'):
            self.error_code = self.__class__.code
        if hasattr(self.__class__, 'message'):
            self.error_message = self.__class__.message
        if code:
            self.error_code = code
        if message:
            self.error_message = message


class APIGenericErrorResponse(APIErrorResponse):
    code = 0x1000
    message = "An error occurred"


class APIInvalidRequestErrorResponse(APIErrorResponse):
    code = 0x1001
    message = "Invalid API request"

    def __init__(self, message=None):
        super(APIInvalidRequestErrorResponse, self).__init__()
        if message:
            self.error_message = message

class APIPluginNotFoundErrorResponse(APIErrorResponse):
    code = 0x1002
    message = "Plugin was not found for request"


class APIDebuggerHostNotSupportedErrorResponse(APIErrorResponse):
    code = 0x1003
    message = "The targeted debugger host is not supported by this plugin"


class APITimedOutErrorResponse(APIErrorResponse):
    code = 0x1004
    message = "The request timed out"


class APIDebuggerNotPresentErrorResponse(APIErrorResponse):
    code = 0x1004
    message = "No debugger host was found"


class APINoSuchTargetErrorResponse(APIErrorResponse):
    code = 0x1005
    message = "No such target"


class APITargetBusyErrorResponse(APIErrorResponse):
    code = 0x1006
    message = "Target busy"
