import logging
import os
from flask import *

from .plugin import *
from .api import *

app = Flask('voltron', template_folder='web/templates')
log = logging.getLogger('api')


@app.route("/api/request", methods=['POST'])
def handle_post():
    """
    Requests  are proxied straight through to the server's handle_request()
    method. The entire request body is treated as a JSON request and passed
    through unmodified.

    e.g.
    POST /api/request HTTP/1.1

    {"type": "request", "request": "version"}
    """
    res = app.server.handle_request(str(request.data))
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
    res = app.server.dispatch_request(api_request(request.path.split('/')[-1], **request.args.to_dict()))
    return Response(str(res), status=200, mimetype='application/json')

def register_http_api():
    """
    Register URL routes for each API plugin. All routes go to handle_get().

    e.g. Registers '/api/version' to call handle_get()
    """
    for plugin in voltron.plugin.pm.api_plugins:
        app.add_url_rule('/api/{}'.format(plugin), plugin, handle_get)

@app.route("/")
def root():
    return make_response(render_template('index.html', views=voltron.plugin.pm.web_plugins.keys()))