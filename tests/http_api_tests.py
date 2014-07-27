"""
Tests that emulate the debugger adaptor and just test the interaction between
the front end and back end API classes. HTTP edition!

Tests:
Server (via HTTP)
"""

import logging
import sys
import json
import time
import subprocess
import requests

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

    # inject mock methods
    inject_mock(adaptor)

    # start up a voltron server
    server = Server()
    server.start()

    time.sleep(2)

def teardown():
    server.stop()

def test_disassemble():
    data = requests.get('http://localhost:5555/api/disassemble?count=16').text
    res = APIResponse(data=data)
    assert res.is_success
    assert res.disassembly == disassemble_response

def test_execute_command():
    data = requests.get('http://localhost:5555/api/execute_command?command=reg%20read').text
    res = APIResponse(data=data)
    assert res.is_success
    assert res.output == execute_command_response

def test_list_targets():
    data = requests.get('http://localhost:5555/api/list_targets').text
    res = api_response('list_targets', data=data)
    assert res.is_success
    assert res.targets == targets_response

def test_read_memory():
    data = requests.get('http://localhost:5555/api/read_registers').text
    res = api_response('read_registers', data=data)
    url = 'http://localhost:5555/api/read_memory?address={}&length=64'.format(res.registers['rip'])
    data = requests.get(url).text
    res = api_response('read_memory', data=data)
    assert res.is_success
    assert res.memory == read_memory_response

def test_read_registers():
    data = requests.get('http://localhost:5555/api/read_registers').text
    res = api_response('read_registers', data=data)
    assert res.is_success
    assert res.registers == read_registers_response

def test_read_stack_length_missing():
    data = requests.get('http://localhost:5555/api/read_stack').text
    res = APIErrorResponse(data=data)
    assert res.is_error
    assert res.message == 'length'

def test_read_stack():
    data = requests.get('http://localhost:5555/api/read_stack?length=64').text
    res = api_response('read_stack', data=data)
    assert res.is_success
    assert res.memory == read_stack_response

def test_state():
    data = requests.get('http://localhost:5555/api/state').text
    res = api_response('state', data=data)
    assert res.is_success
    assert res.state == state_response

def test_version():
    data = requests.get('http://localhost:5555/api/version').text
    res = api_response('version', data=data)
    assert res.is_success
    assert res.api_version == 1.0
    assert res.host_version == 'lldb-something'

def test_wait():
    data = requests.get('http://localhost:5555/api/wait?timeout=2').text
    res = APIResponse(data=data)
    assert res.is_error
    assert res.code == 0x1004

def test_bad_json():
    data = requests.post('http://localhost:5555/api/request', data='xxx').text
    res = APIResponse(data=data)
    assert res.is_error
    assert res.code == 0x1001

def test_bad_request():
    data = requests.post('http://localhost:5555/api/request', data='{"type":"request","request":"no_such_request"}').text
    res = APIResponse(data=data)
    assert res.is_error
    assert res.code == 0x1002

def test_host_not_supported():
    data = requests.post('http://localhost:5555/api/request', data='{"type":"request","request":"host_not_supported"}').text
    res = APIResponse(data=data)
    assert res.is_error
    assert res.code == 0x1003
