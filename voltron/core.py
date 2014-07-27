import os
import logging
import socket
import select
import threading
import logging
import logging.config
import json
import cherrypy

import voltron
import voltron.http
from .api import *
from .plugin import *
from .api import *

log = logging.getLogger("core")

READ_MAX = 0xFFFF

class Server(object):
    """
    Main server class instantiated by the debugger host. Responsible for
    controlling the background thread that communicates with clients, and
    handling requests forwarded from that thread.
    """
    def __init__(self):
        self.clients = []

        self.d_thread = None
        self.t_thread = None
        self.h_thread = None

        # pipes for controlling ServerThreads
        self.d_exit_out, self.d_exit_in = os.pipe()
        self.t_exit_out, self.t_exit_in = os.pipe()

    def start(self):
        listen = voltron.config['server']['listen']
        if listen['domain']:
            log.debug("Starting server thread for domain socket")
            self.d_thread = ServerThread(self, self.clients, self.d_exit_out, voltron.env['sock'])
            self.d_thread.start()
        if listen['tcp']:
            log.debug("Starting server thread for TCP socket")
            self.t_thread = ServerThread(self, self.clients, self.t_exit_out, tuple(listen['tcp']))
            self.t_thread.start()
        if voltron.config['server']['listen']['http']:
            log.debug("Starting server thread for HTTP server")
            (host, port) = tuple(listen['http'])
            voltron.http.app.server = self
            self.h_thread = HTTPServerThread(self, self.clients, host, port)
            self.h_thread.start()

    def stop(self):
        # terminate the server thread by writing some data to the exit pipe
        log.debug("Stopping server threads")
        if self.d_thread:
            os.write(self.d_exit_in, chr(0))
            self.d_thread.join(10)
        if self.t_thread:
            os.write(self.t_exit_in, chr(0))
            self.t_thread.join(10)
        if self.h_thread:
            self.h_thread.stop()

    def client_summary(self):
        sums = []
        for client in self.clients:
            sums.append(str(client))
        return sums

    def handle_request(self, data, client=None):
        req = None
        res = None

        #
        # preprocess the request to make sure the data and environment are OK
        #

        # make sure we have a debugger, or we're gonna have a bad time
        if voltron.debugger:
            # parse incoming request with the top level APIRequest class so we can determine the request type
            try:
                req = APIRequest(data=data)
            except Exception, e:
                req = None
                log.error("Exception raised while parsing API request: {} {}".format(type(e), e))

            if req:
                # instantiate the request class
                try:
                    req = api_request(req.request, data=data)
                except Exception, e:
                    log.error("Exception raised while creating API request: {} {}".format(type(e), e))
                    req = None
                if not req:
                    res = APIPluginNotFoundErrorResponse()
            else:
                res = APIInvalidRequestErrorResponse()
        else:
            res = APIDebuggerNotPresentErrorResponse()

        #
        # validate and dispatch the request
        #

        if not res:
            # dispatch the request and send the response
            if req and req.request == 'wait':
                # wait requests get handled in a background thread
                t = threading.Thread(target=self.dispatch_request, args=[req, client])
                t.start()
            else:
                # everything else is handled on the main thread
                return self.dispatch_request(req, client)
        else:
            if client:
                # already got an error response and we have a client, send it
                client.send_response(str(res))
            else:
                return res

    def dispatch_request(self, req, client=None):
        """
        Dispatch a request object.
        """
        log.debug("Dispatching request: {}".format(str(req)))

        # make sure it's valid
        res = None
        try:
            req.validate()
        except MissingFieldError, e:
            res = APIMissingFieldErrorResponse(str(e))

        # dispatch the request
        if not res:
            try:
                res = req.dispatch()
            except Exception, e:
                msg = "Exception raised while dispatching request: {}".format(e)
                log.error(msg)
                res = APIGenericErrorResponse(message=msg)

        log.debug("Response: {}".format(str(res)))

        # send the response
        if client:
            log.debug("Client was passed to dispatch_request() - sending response")
            client.send_response(str(res))
        else:
            log.debug("Client was not passed to dispatch_request() - returning response")
            return res


class ServerThread(threading.Thread):
    """
    Background thread spun off by the Server class. Responsible for
    accepting new client connections and communicating with existing clients.
    Requests are received from clients and passed to the Server object, which
    passes them off to the APIDispatcher to be fulfilled. Then the responses
    returned (synchronously) are sent back to the requesting client.
    """
    def __init__(self, server, clients, exit_pipe, sock):
        threading.Thread.__init__(self)
        self.server = server
        self.clients = clients
        self.exit_pipe = exit_pipe
        self.sock = sock

    def run(self):
        # make sure there's no left over socket file
        self.cleanup_socket()

        # set up the server socket
        serv = ServerSocket(self.sock)

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
                        self.server.handle_request(data, fd)
                    except Exception, e:
                        log.error("Exception raised while handling request: {} {}".format(type(e), str(e)))
                        self.purge_client(fd)

        # clean up
        for client in self.clients:
            self.purge_client(client)
        os.close(self.exit_pipe)
        serv.close()
        self.cleanup_socket()

    def cleanup_socket(self):
        if type(self.sock) == str:
            try:
                os.remove(self.sock)
            except:
                pass

    def purge_client(self, client):
        try:
            client.close()
        except:
            pass
        if client in self.clients:
            self.clients.remove(client)


class HTTPServerThread(threading.Thread):
    """
    Background thread to run the HTTP server.
    """
    def __init__(self, server, clients, host="127.0.0.1", port=6969):
        threading.Thread.__init__(self)
        self.server = server
        self.clients = clients
        self.host = host
        self.port = port

    def run(self):
        # register routes for all the API methods
        voltron.http.register_http_api()

        # configure the cherrypy server
        cherrypy.config.update({
            'log.screen': False,
            'server.socket_port': self.port,
            'server.socket_host': str(self.host)
        })

        # mount the main static dir
        cherrypy.tree.mount(None, '/static', {'/' : {
            'tools.staticdir.dir': os.path.join(os.path.dirname(__file__), 'web/static'),
            'tools.staticdir.on': True,
            'tools.staticdir.index': 'index.html'
        }})

        # graft the main flask app (see http.py) onto the cherry tree
        cherrypy.tree.graft(voltron.http.app, '/')

        # mount web plugins
        plugins = voltron.plugin.pm.web_plugins
        for name in plugins:
            plugin_root = '/view/{}'.format(name)
            static_path = '/view/{}/static'.format(name)

            # mount app
            if plugins[name].app:
                # if there's an app object, mount it at the root
                log.debug("Mounting app for web plugin '{}' on {}".format(name, plugin_root))
                plugins[name].app.server = self.server
                cherrypy.tree.graft(plugins[name].app, plugin_root)
            else:
                # if there's no plugin app, mount the static dir at the plugin's root instead
                # neater for static-only apps (ie. javascript-based)
                static_path = plugin_root

            # mount static directory
            directory = os.path.join(plugins[name]._dir, 'static')
            if os.path.isdir(directory):
                log.debug("Mounting static directory for web plugin '{}' on {}: {}".format(name, static_path, directory))
                cherrypy.tree.mount(None, static_path, {'/' : {
                    'tools.staticdir.dir': directory,
                    'tools.staticdir.on': True,
                    'tools.staticdir.index': 'index.html'
                }})


        # make with the serving
        cherrypy.engine.start()
        cherrypy.engine.block()

    def stop(self):
        cherrypy.engine.exit()


class Client(object):
    """
    Used by a client (ie. a view) to communicate with the server.
    """
    def __init__(self):
        """
        Initialise a new client
        """
        self.sock = None

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
            log.debug('Client received message: ' + data)

            try:
                # parse the response data
                generic_response = APIResponse(data=data)

                # if there's an error, return an error response
                if generic_response.is_error:
                    res = APIErrorResponse(data=data)
                else:
                    # success; generate a proper response
                    plugin = voltron.plugin.pm.api_plugin_for_request(request.request)
                    if plugin and plugin.response_class:
                        # found a plugin for the request we sent, use its response type
                        res = plugin.response_class(data=data)
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
        return api_request(request_type, *args, **kwargs)

    def perform_request(self, request_type, *args, **kwargs):
        """
        Create and send a request.

        `request_type` is the request type (string). This is used to look up a
        plugin, whose request class is instantiated and passed the remaining
        arguments passed to this function.
        """
        # create a request
        req = api_request(request_type, *args, **kwargs)

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
    def __init__(self, sock):
        if type(sock) == str:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        elif type(sock) == tuple:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(sock)
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

        log.debug("Received request client -> server: {}".format(data))

        if len(data) == 0:
            raise SocketDisconnected()

        return data

    def send_response(self, response):
        log.debug("Sending response server -> client: {}".format(response))
        self.send(response)
