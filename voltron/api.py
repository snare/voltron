import os
import logging
import socket
import select
import threading
import logging
import logging.config
import json
import inspect
import base64
import six

from collections import defaultdict

from scruffy.plugin import Plugin

import voltron
from .plugin import APIPlugin

log = logging.getLogger('api')

version = 1.1


class InvalidRequestTypeException(Exception):
    """
    Exception raised when the client is requested to send an invalid request type.
    """
    pass


class InvalidDebuggerHostException(Exception):
    """
    Exception raised when the debugger host is invalid.
    """
    pass


class InvalidViewNameException(Exception):
    """
    Exception raised when an invalid view name is specified.
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


class MissingFieldError(Exception):
    """
    Raised when an APIMessage is validated and has a required field missing.
    """
    pass


class NoSuchThreadException(Exception):
    """
    Raised when the specified thread ID or index does not exist.
    """
    pass


class UnknownArchitectureException(Exception):
    """
    Raised when the debugger host is running in an unknown architecture.
    """
    pass


class BlockingNotSupportedError(Exception):
    """
    Raised when a view that does not support blocking connects to a debugger
    host that does not support async mode.
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
        if args and hasattr(args[0], 'is_server') and not voltron.debugger:
            raise ServerSideOnlyException("This method can only be called on a server-side instance")
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
        if args and hasattr(args[0], 'is_server') and voltron.debugger:
            raise ClientSideOnlyException("This method can only be called on a client-side instance")
        return func(*args, **kwargs)
    return inner


def cast_b(val):
    if isinstance(val, six.binary_type):
        return val
    elif isinstance(val, six.text_type):
        return val.encode('latin1')
    return six.binary_type(val)


def cast_s(val):
    if type(val) == six.text_type:
        return val
    elif type(val) == six.binary_type:
        return val.decode('latin1')
    return six.text_type(val)


class APIMessage(object):
    """
    Top-level API message class.
    """
    _top_fields = ['type']
    _fields = {}
    _encode_fields = []

    type = None

    def __init__(self, data=None, *args, **kwargs):
        # process any data that was passed in
        if data:
            self.from_json(data)

        # any other kwargs are treated as field values
        for field in kwargs:
            setattr(self, field, kwargs[field])

    def __str__(self):
        """
        Return a string (JSON) representation of the API message properties.
        """
        return self.to_json()

    def to_dict(self):
        """
        Return a transmission-safe dictionary representation of the API message properties.
        """
        d = {field: getattr(self, field) for field in self._top_fields if hasattr(self, field)}

        # set values of data fields
        d['data'] = {}
        for field in self._fields:
            if hasattr(self, field):
                # base64 encode the field for transmission if necessary
                if field in self._encode_fields:
                    val = getattr(self, field)
                    if val:
                        val = cast_s(base64.b64encode(cast_b(val)))
                    d['data'][field] = val
                else:
                    d['data'][field] = getattr(self, field)

        return d

    def from_dict(self, d):
        """
        Initialise an API message from a transmission-safe dictionary.
        """
        for key in d:
            if key == 'data':
                for dkey in d['data']:
                    if dkey in self._encode_fields:
                        setattr(self, str(dkey), base64.b64decode(d['data'][dkey]))
                    else:
                        setattr(self, str(dkey), d['data'][dkey])
            else:
                setattr(self, str(key), d[key])

    def to_json(self):
        """
        Return a JSON representation of the API message properties.
        """
        return json.dumps(self.to_dict())

    def from_json(self, data):
        """
        Initialise an API message from a JSON representation.
        """
        try:
            d = json.loads(data)
        except ValueError:
            raise InvalidMessageException()
        self.from_dict(d)

    def __getattr__(self, name):
        """
        Attribute accessor.

        If a defined field is requested that doesn't have a value set,
        return None.
        """
        if name in self._fields:
            return None

    def validate(self):
        """
        Validate the message.

        Ensure all the required fields are present and not None.
        """
        required_fields = list(filter(lambda x: self._fields[x], self._fields.keys()))
        for field in (self._top_fields + required_fields):
            if not hasattr(self, field) or hasattr(self, field) and getattr(self, field) == None:
                raise MissingFieldError(field)


class APIRequest(APIMessage):
    """
    An API request object. Contains functions and accessors common to all API
    request types.

    Subclasses of APIRequest are used on both the client and server sides. On
    the server side they are instantiated by Server's `handle_request()`
    method. On the client side they are instantiated by whatever class is doing
    the requesting (probably a view class).
    """
    _top_fields = ['type', 'request', 'block', 'timeout']
    _fields = {}

    type = 'request'
    request = None
    block = False
    timeout = 10

    response = None
    wait_event = None
    timed_out = False

    @server_side
    def dispatch(self):
        """
        In concrete subclasses this method will actually dispatch the request
        to the debugger host and return a response. In this case it raises an
        exception.
        """
        raise NotImplementedError("Subclass APIRequest")

    @server_side
    def wait(self):
        """
        Wait for the request to be dispatched.
        """
        self.wait_event = threading.Event()
        timeout = int(self.timeout) if self.timeout else None
        self.timed_out = not self.wait_event.wait(timeout)

    def signal(self):
        """
        Signal that the request has been dispatched and can return.
        """
        self.wait_event.set()


class APIBlockingRequest(APIRequest):
    """
    An API request that blocks by default.
    """
    block = True


class APIResponse(APIMessage):
    """
    An API response object. Contains functions and accessors common to all API
    response types.

    Subclasses of APIResponse are used on both the client and server sides. On
    the server side they are instantiated by the APIRequest's `dispatch` method
    in order to serialise and send to the client. On the client side they are
    instantiated by the Client class and returned by `send_request`.
    """
    _top_fields = ['type', 'status']
    _fields = {}

    type = 'response'
    status = None

    @property
    def is_success(self):
        return self.status == 'success'

    @property
    def is_error(self):
        return self.status == 'error'

    def __repr__(self):
        return "<%s: success = %s, error = %s, body: %s>" % (
                str(self.__class__),
                self.is_success,
                self.is_error,
                {f: getattr(self, f) for f in self._top_fields + list(self._fields.keys())}
        )


class APISuccessResponse(APIResponse):
    """
    A generic API success response.
    """
    status = 'success'


class APIErrorResponse(APIResponse):
    """
    A generic API error response.
    """
    _fields = {'code': True, 'message': True}

    status = 'error'

    @property
    def timed_out(self):
        return self.code == APITimedOutErrorResponse.code


class APIGenericErrorResponse(APIErrorResponse):
    code = 0x1000
    message = "An error occurred"

    def __init__(self, message=None):
        super(APIGenericErrorResponse, self).__init__()
        if message:
            self.message = message


class APIInvalidRequestErrorResponse(APIErrorResponse):
    code = 0x1001
    message = "Invalid API request"


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


class APIMissingFieldErrorResponse(APIGenericErrorResponse):
    code = 0x1007
    message = "Missing field"


class APIEmptyResponseErrorResponse(APIGenericErrorResponse):
    code = 0x1008
    message = "Empty response"


class APIServerNotRunningErrorResponse(APIGenericErrorResponse):
    code = 0x1009
    message = "Server is not running"
