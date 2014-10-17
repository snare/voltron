"""
Tests that emulate the debugger adaptor and just test the interaction between
the front end and back end API classes.

Tests:
Client -> Server -> APIDispatcher
"""

import tempfile
import sys
import json
import time
import logging
import subprocess
import base64
import time

from mock import Mock
from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import *

import platform
if platform.system() == 'Darwin':
    sys.path.append("/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python")

from common import *

log = logging.getLogger('tests')

class APIHostNotSupportedRequest(APIRequest):
    @server_side
    def dispatch(self):
        return APIDebuggerHostNotSupportedErrorResponse()


class APIHostNotSupportedPlugin(APIPlugin):
    request = "host_not_supported"
    request_class = APIHostNotSupportedRequest
    response_class = APIResponse


def setup():
    global server, client, target, pm, adaptor, methods

    log.info("setting up API tests")

    # set up voltron
    voltron.setup_env()
    pm = PluginManager()
    plugin = pm.debugger_plugin_for_host('lldb')
    adaptor = plugin.adaptor_class()
    voltron.debugger = adaptor

    # update the thingy
    inject_mock(adaptor)

    # start up a voltron server
    server = Server()
    server.start()

    time.sleep(0.1)

    # set up client
    client = Client()
    client.connect()

def teardown():
    server.stop()
    time.sleep(2)

def make_direct_request(request):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(voltron.env['sock'])
    sock.send(request)
    data = sock.recv(0xFFFF)
    return data

def test_direct_invalid_json():
    data = make_direct_request('xxx')
    res = APIResponse(data=data)
    assert res.is_error
    assert res.code == 0x1001

def test_front_end_bad_request():
    req = api_request('version')
    req.request = 'xxx'
    res = client.send_request(req)
    assert res.is_error
    assert res.code == 0x1002

def test_front_end_host_not_supported():
    req = api_request('host_not_supported')
    res = client.send_request(req)
    assert res.is_error
    assert res.code == 0x1003

def test_backend_version():
    res = api_request('version').dispatch()
    assert res.api_version == 1.0
    assert res.host_version == 'lldb-something'

def test_direct_version():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "version"
        }
    ))
    res = api_response('version', data=data)
    assert res.api_version == 1.0
    assert res.host_version == 'lldb-something'

def test_frontend_version():
    req = api_request('version')
    res = client.send_request(req)
    assert res.api_version == 1.0
    assert res.host_version == 'lldb-something'

def test_backend_state():
    res = api_request('state').dispatch()
    assert res.is_success
    assert res.state == "stopped"

def test_direct_state():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "state"
        }
    ))
    res = api_response('state', data=data)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_state():
    req = api_request('state')
    res = client.send_request(req)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_state_with_id():
    req = api_request('state')
    req.target_id = 0
    res = client.send_request(req)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_wait_timeout():
    req = api_request('wait', timeout=2)
    res = client.send_request(req)
    assert res.is_error

def test_backend_targets():
    res = api_request('targets').dispatch()
    assert res.is_success
    assert res.targets == targets_response

def test_direct_targets():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "targets"
        }
    ))
    res = api_response('targets', data=data)
    assert res.is_success
    assert res.targets == targets_response

def test_frontend_targets():
    req = api_request('targets')
    res = client.send_request(req)
    assert res.is_success
    assert res.targets == targets_response

def test_backend_registers():
    res = api_request('registers').dispatch()
    assert res.is_success
    assert res.registers == registers_response

def test_direct_registers():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "registers"
        }
    ))
    res = api_response('registers', data=data)
    assert res.is_success
    assert res.registers == registers_response

def test_frontend_registers():
    req = api_request('registers')
    res = client.send_request(req)
    assert res.is_success
    assert res.registers == registers_response

def test_backend_memory():
    res = api_request('memory', address=0x1000, length=0x40).dispatch()
    assert res.is_success
    assert res.memory == memory_response

def test_direct_memory():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "memory",
            "data": {
                "target_id": 0,
                "address": 0x1000,
                "length": 0x40
            }
        }
    ))
    res = api_response('memory', data=data)
    assert res.is_success
    assert res.memory == memory_response

def test_frontend_memory():
    req = api_request('memory', address=0x1000, length=0x40)
    res = client.send_request(req)
    assert res.is_success
    assert res.memory == memory_response

def test_backend_stack():
    res = api_request('stack', length=0x40).dispatch()
    assert res.is_success
    assert res.memory == stack_response

def test_direct_stack():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "stack",
            "data": {
                "target_id": 0,
                "length": 0x40
            }
        }
    ))
    res = api_response('stack', data=data)
    assert res.is_success
    assert res.memory == stack_response

def test_frontend_stack():
    req = api_request('stack', length=0x40)
    res = client.send_request(req)
    assert res.is_success
    assert res.memory == stack_response

def test_backend_command():
    res = api_request('command', command='reg read').dispatch()
    assert res.is_success
    assert res.output == command_response

def test_direct_command():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "command",
            "data": {
                "command": "reg read"
            }
        }
    ))
    res = api_response('command', data=data)
    assert res.is_success
    assert res.output == command_response

def test_frontend_command():
    req = api_request('command', command='reg read')
    res = client.send_request(req)
    assert res.is_success
    assert res.output == command_response

def test_backend_disassemble():
    res = api_request('disassemble', count=16).dispatch()
    assert res.is_success
    assert res.disassembly == disassemble_response

def test_direct_disassemble():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "disassemble",
            "data": {"count": 16}
        }
    ))
    res = api_response('disassemble', data=data)
    assert res.is_success
    assert res.disassembly == disassemble_response

def test_frontend_disassemble():
    req = api_request('disassemble', count=16)
    res = client.send_request(req)
    assert res.is_success
    assert res.disassembly == disassemble_response
