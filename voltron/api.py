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

from collections import defaultdict

from scruffy.plugin import Plugin

import voltron
from .plugin import APIPlugin

log = logging.getLogger('api')

version = 1.0


class InvalidRequestTypeException(Exception):
    """
    Exception raised when the client is requested to send an invalid request type.
    """
    pass

class InvalidDebuggerHostException(Exception):pass
class InvalidViewNameException(Exception): pass


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
    pass

class UnknownArchitectureException(Exception):
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
            if voltron.debugger:
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
            if not voltron.debugger:
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
    _top_fields = ['type']
    _fields = {}
    _encode_fields = []

    type = None

    def __init__(self, data=None, *args, **kwargs):
        # process any data that was passed in
        if data:
            try:
                d = json.loads(data)
            except ValueError:
                raise InvalidMessageException()
            for key in d:
                if key == 'data':
                    for dkey in d['data']:
                        # base64 decode the field if necessary
                        if dkey in self._encode_fields:
                            setattr(self, str(dkey), base64.b64decode(d['data'][dkey]))
                        else:
                            setattr(self, str(dkey), d['data'][dkey])

                else:
                    setattr(self, str(key), d[key])

        # any other kwargs are treated as field values
        for field in kwargs:
            setattr(self, field, kwargs[field])

    def __str__(self):
        """
        Return a string containing the API message properties in JSON format.
        """
        d = {}
        # set values of top-level fields
        for field in self._top_fields:
            if hasattr(self, field):
                d[field] = getattr(self, field)

        # set values of data fields
        d['data'] = {}
        for field in self._fields:
            if hasattr(self, field):
                # base64 encode the field for transmission if necessary
                if field in self._encode_fields:
                    d['data'][field] = base64.b64encode(str(getattr(self, field)))
                else:
                    d['data'][field] = getattr(self, field)

        return json.dumps(d)

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
    _top_fields = ['type', 'request']
    _fields = {}

    type = 'request'
    request = None

    @server_side
    def dispatch(self):
        """
        In concrete subclasses this method will actually dispatch the request
        to the debugger host and return a response. In this case it raises an
        exception.
        """
        raise NotImplementedError("Subclass APIRequest")


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
                {f: getattr(self, f) for f in self._top_fields + self._fields.keys()}
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
