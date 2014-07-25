import logging
from flask import Flask, request

from .plugin import *
from .api import *

app = Flask('voltron')
log = logging.getLogger('api')

@app.route("/")
def root():
    return 'Voltron. Defender of the universe.'

@app.route("/api", methods=['POST'])
def api():
    return str(app.server.handle_request(str(request.data)))

@app.route("/disassemble")
def disassemble():
    return str(app.server.dispatch_request(api_request('disassemble', **request.args.to_dict())))

@app.route("/execute_command")
def execute_command():
    return str(app.server.dispatch_request(api_request('execute_command', **request.args.to_dict())))

@app.route("/list_breakpoints")
def list_breakpoints():
    return str(app.server.dispatch_request(api_request('list_breakpoints', **request.args.to_dict())))

@app.route("/list_targets")
def list_targets():
    return str(app.server.dispatch_request(api_request('list_targets', **request.args.to_dict())))

@app.route("/read_memory")
def read_memory():
    return str(app.server.dispatch_request(api_request('read_memory', **request.args.to_dict())))

@app.route("/read_registers")
def read_registers():
    return str(app.server.dispatch_request(api_request('read_registers', **request.args.to_dict())))

@app.route("/read_stack")
def read_stack():
    req = api_request('read_stack', **request.args.to_dict())
    return str(app.server.dispatch_request(req))

@app.route("/state")
def state():
    return str(app.server.dispatch_request(api_request('state', **request.args.to_dict())))

@app.route("/version")
def version():
    return str(app.server.dispatch_request(api_request('version')))

@app.route("/wait")
def wait():
    return str(app.server.dispatch_request(api_request('wait', **request.args.to_dict())))

