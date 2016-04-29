import os
import sys
import errno
import logging
import socket
import select
import threading
import logging
import logging.config
import json
try:
    import requests_unixsocket as requests
except:
    import requests
import threading
import os.path
import pkgutil

from werkzeug.serving import WSGIRequestHandler, BaseWSGIServer, ThreadedWSGIServer
from werkzeug.wsgi import SharedDataMiddleware, DispatcherMiddleware

from flask import Flask, request, Response, render_template, make_response, redirect

import voltron
from .api import *
from .plugin import *

import six
if six.PY2:
    if sys.platform == 'win32':
        from SocketServer import ThreadingMixIn
    else:
        from SocketServer import UnixStreamServer, ThreadingMixIn
    from BaseHTTPServer import HTTPServer
else:
    if sys.platform == 'win32':
        from six.moves.socketserver import ThreadingMixIn
    else:
        from six.moves.socketserver import UnixStreamServer, ThreadingMixIn
    from six.moves.BaseHTTPServer import HTTPServer

try:
    from voltron_web import app as ui_app
except:
    ui_app = None

logging.getLogger("requests").setLevel(logging.WARNING)


def get_loader(name):
    try:
        return orig_get_loader(name)
    except AttributeError:
        pass
orig_get_loader = pkgutil.get_loader
pkgutil.get_loader = get_loader


# make sure we use HTTP 1.1 for keep-alive
WSGIRequestHandler.protocol_version = "HTTP/1.1"

log = logging.getLogger("core")

if sys.version_info.major == 2:
    STRTYPES = (str, unicode)
elif sys.version_info.major == 3:
    STRTYPES = (str, bytes)
else:
    raise RuntimeError("Not sure what strings look like on python %d" %
                       sys.version_info.major)


class APIFlaskApp(Flask):
    """
    A Flask app for the API.
    """
    def __init__(self, *args, **kwargs):
        if 'server' in kwargs:
            self.server = kwargs['server']
            del kwargs['server']
        super(APIFlaskApp, self).__init__('voltron_api', *args, **kwargs)

        def api_post():
            res = self.server.handle_request(request.data.decode('UTF-8'))
            return Response(str(res), status=200, mimetype='application/json')

        def api_get():
            res = self.server.handle_request(str(api_request(request.path.split('/')[-1], **request.args.to_dict())))
            return Response(str(res), status=200, mimetype='application/json')

        # Handle API POST requests at /api/request
        api_post.methods = ["POST"]
        self.add_url_rule('/request', 'request', api_post)

        # Handle API GET requests at /api/<request_name> e.g. /api/version
        for plugin in voltron.plugin.pm.api_plugins:
            self.add_url_rule('/{}'.format(plugin), plugin, api_get)


class RootFlaskApp(Flask):
    """
    A Flask app for /.
    """
    def __init__(self, *args, **kwargs):
        super(RootFlaskApp, self).__init__('voltron', *args, **kwargs)

        def index():
            if ui_app:
                return redirect('/ui')
            else:
                return "The Voltron web interface is not installed. Install the <tt>voltron-web</tt> package with <tt>pip</tt>."

        self.add_url_rule('/', 'index', index)


class Server(object):
    """
    Main server class instantiated by the debugger host. Responsible for
    controlling the background thread that communicates with clients, and
    handling requests forwarded from that thread.
    """
    def __init__(self):
        self.threads = []
        self.listeners = []
        self.is_running = False
        self.queue = []
        self.queue_lock = threading.Lock()

    def start(self):
        """
        Start the server.
        """
        plugins = voltron.plugin.pm.web_plugins
        self.app = DispatcherMiddleware(
            RootFlaskApp(),
            {
                "/api": APIFlaskApp(server=self),
                "/view": SharedDataMiddleware(
                    None,
                    {'/{}'.format(n): os.path.join(p._dir, 'static') for (n, p) in six.iteritems(plugins)}
                ),
                "/ui": ui_app
            }
        )

        def run_listener(name, cls, arg):
            log.debug("Starting listener for {} socket on {}".format(name, str(arg)))
            s = cls(*arg)
            t = threading.Thread(target=s.serve_forever)
            t.start()
            self.threads.append(t)
            self.listeners.append(s)

        if voltron.config.server.listen.tcp:
            run_listener('tcp', ThreadedVoltronWSGIServer, list(voltron.config.server.listen.tcp) + [self.app])

        if voltron.config.server.listen.domain and sys.platform != 'win32':
            path = os.path.expanduser(str(voltron.config.server.listen.domain))
            try:
                os.unlink(path)
            except:
                pass
            run_listener('domain', ThreadedUnixWSGIServer, [path, self.app])

        self.is_running = True

    def stop(self):
        """
        Stop the server.
        """
        log.debug("Stopping listeners")
        self.queue_lock.acquire()
        for s in self.listeners:
            log.debug("Stopping {}".format(s))
            s.shutdown()
            s.socket.close()
        self.cancel_queue()
        for t in self.threads:
            t.join()
        self.listeners = []
        self.threads = []
        self.is_running = False
        self.queue_lock.release()
        log.debug("Listeners stopped and threads joined")

    def handle_request(self, data):
        req = None
        res = None

        if self.is_running:
            # make sure we have a debugger, or we're gonna have a bad time
            if voltron.debugger:
                # parse incoming request with the top level APIRequest class so we can determine the request type
                try:
                    req = APIRequest(data=data)
                except Exception as e:
                    req = None
                    log.exception("Exception raised while parsing API request: {} {}".format(type(e), e))

                if req:
                    # instantiate the request class
                    try:
                        log.debug("data = {}".format(data))
                        req = api_request(req.request, data=data)
                    except Exception as e:
                        log.exception("Exception raised while creating API request: {} {}".format(type(e), e))
                        req = None
                    if not req:
                        res = APIPluginNotFoundErrorResponse()
                else:
                    res = APIInvalidRequestErrorResponse()
            else:
                res = APIDebuggerNotPresentErrorResponse()

            if not res:
                # no errors so far, queue the request and wait
                if req and req.block:
                    self.queue_lock.acquire()
                    self.queue.append(req)
                    self.queue_lock.release()

                    # When this returns the request will have been processed by the dispatch_queue method on the main
                    # thread (or timed out). We have to do it this way because GDB sucks.
                    req.wait()

                    if req.timed_out:
                        res = APITimedOutErrorResponse()
                    else:
                        res = req.response

                    # Remove the request from the queue
                    self.queue_lock.acquire()
                    if req in self.queue:
                        self.queue.remove(req)
                    self.queue_lock.release()
                else:
                    # non-blocking, dispatch request straight away
                    res = self.dispatch_request(req)
        else:
            res = APIServerNotRunningErrorResponse()

        return res

    def cancel_queue(self):
        """
        Cancel all requests in the queue so we can exit.
        """
        q = list(self.queue)
        self.queue = []
        log.debug("Canceling requests: {}".format(q))
        for req in q:
            req.response = APIServerNotRunningErrorResponse()
        for req in q:
            req.signal()

    def dispatch_queue(self):
        """
        Dispatch any queued requests.

        Called by the debugger when it stops.
        """
        self.queue_lock.acquire()
        q = list(self.queue)
        self.queue = []
        self.queue_lock.release()
        log.debug("Dispatching requests: {}".format(q))
        for req in q:
            req.response = self.dispatch_request(req)
        for req in q:
            req.signal()

    def dispatch_request(self, req):
        """
        Dispatch a request object.
        """
        log.debug("Dispatching request: {}".format(str(req)))

        # make sure it's valid
        res = None
        try:
            req.validate()
        except MissingFieldError as e:
            res = APIMissingFieldErrorResponse(str(e))

        # dispatch the request
        if not res:
            try:
                res = req.dispatch()
            except Exception as e:
                msg = "Exception raised while dispatching request: {}".format(repr(e))
                log.exception(msg)
                res = APIGenericErrorResponse(msg)

        log.debug("Response: {}".format(str(res)))

        return res


class VoltronWSGIServer(BaseWSGIServer):
    """
    Custom version of the werkzeug WSGI server.

    This just needs to exist so we can swallow errors when clients disconnect.
    """
    clients = []

    def finish_request(self, *args):
        self.clients.append(args[0])
        log.debug("finish_request({})".format(args))
        try:
            super(VoltronWSGIServer, self).finish_request(*args)
        except socket.error as e:
            log.error("Error in finish_request: {}".format(e))

    def shutdown(self):
        super(VoltronWSGIServer, self).shutdown()
        for c in self.clients:
            try:
                c.shutdown(socket.SHUT_RD)
                c.close()
            except:
                pass


class ThreadedVoltronWSGIServer(ThreadingMixIn, VoltronWSGIServer):
    """
    Threaded WSGI server to replace werkzeug's
    """
    pass


if sys.platform != 'win32':
    class UnixWSGIServer(UnixStreamServer, VoltronWSGIServer):
        """
        A subclass of BaseWSGIServer that does sane things with Unix domain sockets.
        """
        def __init__(self, sockfile=None, app=None):
            self.address_family = socket.AF_UNIX
            UnixStreamServer.__init__(self, sockfile, UnixWSGIRequestHandler)
            self.app = app
            self.passthrough_errors = None
            self.shutdown_signal = False
            self.ssl_context = None
            self.host = 'localhost'
            self.port = 0

    class UnixWSGIRequestHandler(WSGIRequestHandler):
        """
        A WSGIRequestHandler that does sane things with Unix domain sockets.
        """
        def make_environ(self, *args, **kwargs):
            self.client_address = ('127.0.0.1', 0)
            return super(UnixWSGIRequestHandler, self).make_environ(*args, **kwargs)

    class ThreadedUnixWSGIServer(ThreadingMixIn, UnixWSGIServer):
        """
        Threaded HTTP server that works over Unix domain sockets.

        Note: this intentionally does not inherit from HTTPServer. Go look at the
        source and you'll see why.
        """
        multithread = True


class ClientThread(threading.Thread):
    """
    A thread that performs an API request with a client.
    """
    def __init__(self, client, request, *args, **kwargs):
        self.request = request
        self.response = None
        self.exception = None
        self.client = client
        super(ClientThread, self).__init__(*args, **kwargs)

    def run(self):
        try:
            self.response = self.client.send_request(self.request)
        except Exception as e:
            self.exception = e


class Client(object):
    """
    Used by a client (ie. a view) to communicate with the server.
    """
    def __init__(self, host='127.0.0.1', port=5555, sockfile=None, url=None):
        """
        Initialise a new client
        """
        self.session = requests.Session()
        if url:
            self.url = url
        elif sockfile:
            self.url = 'http+unix://{}/api/request'.format(sockfile.replace('/', '%2F'))
        else:
            self.url = 'http://{}:{}/api/request'.format(host, port)
        self.url = self.url.replace('~', os.path.expanduser('~').replace('/', '%2f'))

    def send_request(self, request):
        """
        Send a request to the server.

        `request` is an APIRequest subclass.

        Returns an APIResponse or subclass instance. If an error occurred, it
        will be an APIErrorResponse, if the request was successful it will be
        the plugin's specified response class if one exists, otherwise it will
        be an APIResponse.
        """
        # default to an empty response error
        res = APIEmptyResponseErrorResponse()

        # perform the request
        log.debug("Client sending request: " + str(request))
        response = self.session.post(self.url, data=str(request))
        data = response.text
        if response.status_code != 200:
            res = APIGenericErrorResponse(response.text)
        elif data and len(data) > 0:
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
                log.exception('Exception parsing message: ' + str(e))
                log.error('Invalid message: ' + data)
        else:
            res = APIEmptyResponseErrorResponse()

        return res

    def send_requests(self, *args):
        """
        Send a set of requests.

        Each request is sent over its own connection and the function will
        return when all the requests have been fulfilled.
        """
        threads = [ClientThread(self, req) for req in args]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        exceptions = [t.exception for t in threads if t.exception]
        if len(exceptions):
            raise exceptions[0]
        return [t.response for t in threads]

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
