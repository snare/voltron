import os
import logging
import socket
import select
import threading
import logging
import logging.config
import json

import voltron
from .api import *
from .plugin import PluginManager

log = logging.getLogger("core")

READ_MAX = 0xFFFF

class Server(object):
    """
    Main server class instantiated by the debugger host. Responsible for
    controlling the background thread that communicates with clients, and
    handling requests forwarded from that thread.
    """
    def __init__(self, debugger=None, plugin_mgr=None):
        self.clients = []

        # pipes for controlling ServerThread
        self.exit_out, self.exit_in = os.pipe()

        self.debugger = debugger
        if plugin_mgr:
            self.plugin_mgr = plugin_mgr
        else:
            self.plugin_mgr = PluginManager()

    def start(self):
        # spin off a server thread
        log.debug("Starting server thread")
        self.thread = ServerThread(self, self.clients, self.exit_out, self.debugger, self.plugin_mgr)
        self.thread.start()

    def stop(self):
        # terminate the server thread by writing some data to the exit pipe
        log.debug("Stopping server thread")
        os.write(self.exit_in, chr(0))
        self.thread.join(10)

    def client_summary(self):
        sums = []
        for client in self.clients:
            sums.append(str(client))
        return sums


class ServerThread(threading.Thread):
    """
    Background thread spun off by the Server class. Responsible for
    accepting new client connections and communicating with existing clients.
    Requests are received from clients and passed to the Server object, which
    passes them off to the APIDispatcher to be fulfilled. Then the responses
    returned (synchronously) are sent back to the requesting client.
    """
    def __init__(self, server, clients, exit_pipe, debugger, plugin_mgr):
        threading.Thread.__init__(self)
        self.server = server
        self.clients = clients
        self.exit_pipe = exit_pipe
        self.debugger = debugger
        self.plugin_mgr = plugin_mgr

    def run(self):
        # make sure there's no left over socket
        try:
            os.remove(voltron.env['sock'])
        except:
            pass

        # set up the server socket
        serv = ServerSocket(voltron.env['sock'])
        self.lock = threading.Lock()

        # main event loop
        running = True
        while running:
            # check server accept() socket, exit pipe, and client sockets for activity
            rfds, _, _ = select.select([serv, self.exit_pipe] + self.clients, [], [])

            # handle any ready sockets
            for fd in rfds:
                if fd == serv:
                    # accept a new client connection
                    client = serv.accept()
                    client.server = self.server
                    self.clients.append(client)
                elif fd == self.exit_pipe:
                    # flush the exit pipe and break
                    os.read(self.exit_pipe, 1)
                    running = False
                    break
                else:
                    # read the request from the client and dispatch it
                    data = None
                    try:
                        data = fd.recv_request()
                        self.handle_request(data, fd)
                    except socket.error:
                        log.error("Socket error")
                        self.purge_client(fd)
                    except SocketDisconnected:
                        log.error("Socket disconnected")
                        self.purge_client(fd)

        # clean up
        for client in self.clients:
            self.purge_client(client)
        os.close(self.exit_pipe)
        serv.close()
        try:
            os.remove(voltron.env['sock'])
        except:
            pass

    def purge_client(self, client):
        try:
            client.close()
        except:
            pass
        if client in self.clients:
            self.clients.remove(client)

    def handle_request(self, data, client):
        res = None

        log.debug("Received API request: {}".format(data))

        # preprocess the request to determine whether or not it needs to be dispatched in a background thread
        try:
            req = APIRequest(data=data, debugger=self.debugger)
        except Exception, e:
            req = None
            log.error(log.error("Exception raised while parsing API request: {}".format(e)))

        # dispatch the request and send the response
        if req and req.request == 'wait':
            # wait requests get handled in a background thread
            t = threading.Thread(target=self.dispatch_request, args=[data, client])
            t.start()
        else:
            # everything else is handled on the main thread
            self.dispatch_request(data, client)

    def dispatch_request(self, data, client):
        """
        Dispatch an API request. This method parses the data, determines the
        request type, looks up the appropriate plugin, uses it to carry out
        the request and sends the response to the client.

        This function may be run in a background thread in order to process a
        request that blocks without interfering with the main thread.
        """
        # make sure we have a debugger, or we're gonna have a bad time
        if self.debugger:
            # parse incoming request with the top level APIRequest class so we can determine the request type
            try:
                req = APIRequest(data=data, debugger=self.debugger)
            except Exception, e:
                req = None
                log.error(log.error("Exception raised while parsing API request: {}".format(e)))

            if req:
                # find the api plugin for the incoming request type
                plugin = self.plugin_mgr.api_plugin_for_request(req.request)
                if plugin:
                    # make sure request class supports the debugger platform we're using
                    # XXX do this

                    if True:
                        # instantiate the request class
                        req = plugin.request_class(data=data, debugger=self.debugger)

                        # make sure it's valid
                        res = None
                        try:
                            req.validate()
                        except InvalidMessageException, e:
                            res = APIInvalidRequestErrorResponse(str(e))

                        if not res:
                            # dispatch the request
                            try:
                                res = req.dispatch()
                            except Exception, e:
                                msg = "Exception raised while dispatching request: {}".format(e)
                                log.error(msg)
                                res = APIGenericErrorResponse(message=msg)
                    else:
                        res = APIDebuggerHostNotSupportedErrorResponse()
                else:
                    res = APIPluginNotFoundErrorResponse()
            else:
                res = APIInvalidRequestErrorResponse()
        else:
            res = APIDebuggerNotPresentErrorResponse()

        log.debug("Returning API response: {} {}".format(type(res), str(res)))

        # send the response
        try:
            client.send_response(str(res))
        except Exception, e:
            log.error("Exception {} sending response: {}".format(type(e), e))
            self.purge_client(client)


class Client(object):
    """
    Used by a client application (ie. a view) to communicate with the server.
    """
    def __init__(self):
        """
        Initialise a new client
        """
        self.sock = None
        self.plugin_mgr = PluginManager()

    def connect(self):
        """
        Connect to the server
        """
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(voltron.env['sock'])

    def send_request(self, request):
        """
        Send a request to the server.

        `request` is an APIRequest subclass.

        Returns an APIResponse or subclass instance. If an error occurred, it
        will be an APIErrorResponse, if the request was successful it will be
        the plugin's specified response class if one exists, otherwise it will
        be an APIResponse.
        """
        # send the request data to the server
        data = str(request)
        log.debug("Sending request: {}".format(data))
        res = self.sock.sendall(data)
        if res != None:
            log.error("Failed to send request: {}".format(request))
            raise SocketDisconnected("socket closed")

        # receive response data
        data = self.sock.recv(READ_MAX)
        if len(data) > 0:
            log.debug('Received message: ' + data)

            try:
                # parse the response data
                generic_response = APIResponse(data=data)

                # if there's an error, return an error response
                if generic_response.is_error:
                    res = APIErrorResponse(code=generic_response.error_code, message=generic_response.error_message)
                else:
                    # success; generate a proper response
                    plugin = self.plugin_mgr.api_plugin_for_request(request.request)
                    if plugin and plugin.response_class:
                        # found a plugin for the request we sent, use its response type
                        res = plugin.response_class()
                        res.props = generic_response.props
                    else:
                        # didn't find a plugin, just return the generic APIResponse we already generated
                        res = generic_response
            except Exception as e:
                log.error('Exception parsing message: ' + str(e))
                log.error('Invalid message: ' + data)
        else:
            raise SocketDisconnected("socket closed")

        return res

    def create_request(self, request_type, *args, **kwargs):
        """
        Create a request.

        `request_type` is the request type (string). This is used to look up a
        plugin, whose request class is instantiated and passed the remaining
        arguments passed to this function.
        """
        # look up the plugin
        plugin = self.plugin_mgr.api_plugin_for_request(request_type)
        if plugin and plugin.request_class:
            #create a request
            req = plugin.request_class(*args, **kwargs)
        else:
            raise InvalidRequestTypeException()

        return req

    def perform_request(self, request_type, *args, **kwargs):
        """
        Create and send a request.

        `request_type` is the request type (string). This is used to look up a
        plugin, whose request class is instantiated and passed the remaining
        arguments passed to this function.
        """
        # create a request
        req = self.create_request(request_type, *args, **kwargs)

        # send it
        res = self.send_request(req)

        return res


class SocketDisconnected(Exception):
    """
    Exception raised when a socket disconnects.
    """
    pass


class BaseSocket(object):
    """
    Base socket class from which ServerSocket and ClientSocket inherit.
    """
    def fileno(self):
        return self.sock.fileno()

    def close(self):
        self.sock.close()

    def send(self, buf):
        self.sock.sendall(buf)


class ServerSocket(BaseSocket):
    """
    Server socket for accepting new client connections.
    """
    def __init__(self, sockfile):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(sockfile)
        self.sock.listen(1)

    def accept(self):
        pair = self.sock.accept()
        if pair is not None:
            sock, addr = pair
            try:
                return ClientSocket(sock)
            except Exception as e:
                log.error("Exception handling accept: " + str(e))


class ClientSocket(BaseSocket):
    """
    Client socket for communicating with an individual client. Collected by
    ServerThread.
    """
    def __init__(self, sock):
        self.sock = sock

    def recv_request(self):
        # read request from socket
        data = self.sock.recv(READ_MAX).strip()

        # if len(data) == 0
        return data

    def send_response(self, response):
        self.send(response)

