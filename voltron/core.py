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
import cherrypy
import requests
import requests_unixsocket
import threading

from flask import Flask, request, Response

import voltron
from .api import *
from .plugin import *
from .api import *

log = logging.getLogger("core")

READ_MAX = 0xFFFF

if sys.version_info.major == 2:
    STRTYPES = (str, unicode)
elif sys.version_info.major == 3:
    STRTYPES = (str, bytes)
else:
    raise RuntimeError("Not sure what strings look like on python %d" %
                       sys.version_info.major)


class Server(object):
    """
    Main server class instantiated by the debugger host. Responsible for
    controlling the background thread that communicates with clients, and
    handling requests forwarded from that thread.
    """
    def __init__(self):
        self.thread = None
        self.is_running = False
        self.queue = []

    def start(self):
        listen = voltron.config['server']['listen']
        if voltron.config['server']['listen']['http']:
            log.debug("Starting server thread for HTTP server")
            (host, port) = tuple(listen['http'])
            self.thread = HTTPServerThread(self, host, port)
            self.thread.start()
        self.is_running = True

    def stop(self):
        if self.thread:
            log.debug("Stopping HTTP server")
            self.thread.stop()
        self.is_running = False

    def handle_request(self, data):
        req = None
        res = None

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
                self.queue.append(req)

                # When this returns the request will have been processed by the dispatch_queue method on the main
                # thread (or timed out). We have to do it this way because GDB sucks. dispatch_queue will remove
                # dispatched requests from the queue, but each client connection's thread will have a reference to
                # the relevant request here waiting.
                req.wait()

                if req.timed_out:
                    res = APITimedOutErrorResponse()
                else:
                    res = req.response
            else:
                # non-blocking, dispatch request straight away
                res = self.dispatch_request(req)

        return res

    def dispatch_queue(self):
        """
        Dispatch any queued requests.

        Called by the debugger when it stops.
        """
        for req in self.queue:
            req.response = self.dispatch_request(req)
            req.signal()
        self.queue = []

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
                msg = "Exception raised while dispatching request: {}".format(e)
                log.exception(msg)
                res = APIGenericErrorResponse(msg)

        log.debug("Response: {}".format(str(res)))

        return res


class VoltronFlaskApp(Flask):
    """
    A Voltron Flask app.
    """
    def __init__(self, *args, **kwargs):
        if 'server' in kwargs:
            self.server = kwargs['server']
            del kwargs['server']
        super(VoltronFlaskApp, self).__init__(*args, **kwargs)


class HTTPServerThread(threading.Thread):
    """
    Background thread to run the HTTP server.
    """
    def __init__(self, server, host="127.0.0.1", port=5555):
        threading.Thread.__init__(self)
        self.server = server
        self.host = host
        self.port = port

    def run(self):
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

        # create the main flask app
        app = VoltronFlaskApp('voltron', template_folder='web/templates', server=self.server)

        def handle_post():
            """
            Requests  are proxied straight through to the server's handle_request()
            method. The entire request body is treated as a JSON request and passed
            through unmodified.

            e.g.
            POST /api/request HTTP/1.1

            {"type": "request", "request": "version"}
            """
            res = app.server.handle_request(request.data.decode('UTF-8'))
            return Response(str(res), status=200, mimetype='application/json')

        def handle_get():
            """
            Handle an incoming HTTP API request via the GET method.

            Query string parameters from the request are passed through as kwargs to
            the api_request() function, which will create an API request of the
            specified type with those args, then the resultant request is dispatched
            and the result returned.

            e.g. GET /api/execute_command?command=version HTTP/1.1

            Routes to this method are registered by register_http_api()
            """
            res = app.server.handle_request(api_request(request.path.split('/')[-1], **request.args.to_dict()))
            return Response(str(res), status=200, mimetype='application/json')

        # set up request routing, etc and graft it onto the cherry tree
        handle_post.methods = ['POST']
        app.add_url_rule('/api/request', 'request', handle_post)
        for plugin in voltron.plugin.pm.api_plugins:
            app.add_url_rule('/api/{}'.format(plugin), plugin, handle_get)
        cherrypy.tree.graft(app, '/')

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
        log.debug("Killed cherrypy")


class ClientThread(threading.Thread):
    """
    A thread that performs an API request with a client.
    """
    def __init__(self, client, request, *args, **kwargs):
        self.request = request
        self.response = None
        self.client = client
        super(ClientThread, self).__init__(*args, **kwargs)

    def run(self):
        self.response = self.client.send_request(self.request)


class Client(object):
    """
    Used by a client (ie. a view) to communicate with the server.
    """
    def __init__(self, host='127.0.0.1', port=5555, sockfile=None):
        """
        Initialise a new client
        """
        self.session = requests_unixsocket.Session()
        if sockfile:
            self.url = 'http+unix://{}/api/request'.format(sockfile.replace('/', '%2F'))
        else:
            self.url = 'http://{}:{}/api/request'.format(host, port)

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
        response = self.session.post(self.url, data=str(request).encode('UTF-8'))
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
        return [t.response for t in threads]
        # reqs = [gevent.spawn(self.send_request, req) for req in args]
        # print "joining"
        # gevent.joinall(reqs)
        # return [req.value for req in reqs]

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
