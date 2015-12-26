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

from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import *

import platform
if platform.system() == 'Darwin':
    sys.path.append("/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python")

from .common import *

import requests


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
    voltron.config['server'] = {
        "listen": {
            "tcp":     ["127.0.0.1", 5555]
        }
    }
    pm = PluginManager()
    plugin = pm.debugger_plugin_for_host('mock')
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
    time.sleep(2)


def test_disassemble():
    data = requests.get('http://localhost:5555/api/disassemble?count=16').text
    res = APIResponse(data=data)
    assert res.is_success
    assert res.disassembly == disassemble_response


def test_command():
    data = requests.get('http://localhost:5555/api/command?command=reg%20read').text
    res = APIResponse(data=data)
    assert res.is_success
    assert res.output == command_response


def test_targets():
    data = requests.get('http://localhost:5555/api/targets').text
    res = api_response('targets', data=data)
    assert res.is_success
    assert res.targets == targets_response


def test_memory():
    data = requests.get('http://localhost:5555/api/registers').text
    res = api_response('registers', data=data)
    url = 'http://localhost:5555/api/memory?address={}&length=64'.format(res.registers['rip'])
    data = requests.get(url).text
    res = api_response('memory', data=data)
    assert res.is_success
    assert res.memory == memory_response


def test_registers():
    data = requests.get('http://localhost:5555/api/registers').text
    res = api_response('registers', data=data)
    assert res.is_success
    assert res.registers == registers_response


def test_stack_length_missing():
    data = requests.get('http://localhost:5555/api/stack').text
    res = APIErrorResponse(data=data)
    assert res.is_error
    assert res.message == 'length'


def test_stack():
    data = requests.get('http://localhost:5555/api/stack?length=64').text
    res = api_response('stack', data=data)
    assert res.is_success
    assert res.memory == stack_response


def test_state():
    data = requests.get('http://localhost:5555/api/state').text
    res = api_response('state', data=data)
    assert res.is_success
    assert res.state == state_response


def test_version():
    data = requests.get('http://localhost:5555/api/version').text
    res = api_response('version', data=data)
    assert res.is_success
    assert res.api_version == 1.1
    assert res.host_version == 'lldb-something'


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


def test_breakpoints():
    data = requests.get('http://localhost:5555/api/breakpoints').text
    res = api_response('breakpoints', data=data)
    assert res.is_success
    assert res.breakpoints == breakpoints_response
