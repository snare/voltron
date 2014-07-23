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

from mock import Mock
from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import PluginManager, DebuggerAdaptorPlugin

import platform
if platform.system() == 'Darwin':
    sys.path.append("/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python")

from common import *

log = logging.getLogger(__name__)

state_response = "stopped"
targets_response = [{
    "id":       0,
    "file":     "/bin/ls",
    "arch":     "x86_64",
    "state":     "stopped"
}]
read_registers_response = ({"gs": 0, "fooff": 0, "edi": 1, "edx": 1349115624, "r13w": 0, "r8l": 0, "fiseg": 0, "r8d": 0,
    "r13d": 0, "r13l": 0, "fstat": 0, "r8w": 0, "ymm9": "n/a", "ymm8": "n/a", "r14": 0, "r15": 0, "r12": 0, "r13": 0,
    "dh": 222, "di": 1, "ymm1": "n/a", "ymm0": "n/a", "ymm3": "n/a", "ymm2": "n/a", "ymm5": "n/a", "ymm4": "n/a",
    "ymm7": "n/a", "ymm6": "n/a", "dx": 57064, "dil": 1, "xmm6": "n/a", "r10l": 0, "bpl": 200, "r10d": 1349110784,
    "xmm10": "n/a", "xmm11": "n/a", "xmm12": "n/a", "xmm13": "n/a", "xmm14": "n/a", "xmm15": "n/a", "fioff": 0,
    "sil": 216, "r10w": 52224, "mxcsr": 8064, "ebp": 1349115592, "ebx": 0, "r15d": 0, "fop": 0, "esp": 1349115576,
    "r15l": 0, "r15w": 0, "ftag": 0, "esi": 1349115608, "bl": 0, "bh": 0, "xmm2": "n/a", "xmm3": "n/a", "xmm0": "n/a",
    "xmm1": "n/a", "bp": 57032, "xmm7": "n/a", "xmm4": "n/a", "xmm5": "n/a", "xmm8": "n/a", "xmm9": "n/a", "bx": 0,
    "ecx": 1349115632, "r9l": 0, "dl": 232, "r12w": 0, "r9d": 1349111808, "r8": 0, "rdx": 140734542503656, "r12d": 0,
    "r9w": 53248, "rdi": 1, "r12l": 0, "ch": 222, "cl": 240, "stmm4": "n/a", "stmm5": "n/a", "stmm6": "n/a", "stmm7":
    "n/a", "stmm0": "n/a", "stmm1": "n/a", "stmm2": "n/a", "stmm3": "n/a", "cx": 57072, "cs": 43,
    "rcx": 140734542503664, "rflags": 582, "rsi": 140734542503640, "mxcsrmask": 65535, "eax": 257305888,
    "rsp": 140734542503608, "trapno": 3, "r14d": 0, "faultvaddr": 4552486912, "err": 0, "rbx": 0, "r14l": 0,
    "rbp": 140734542503624, "r14w": 0, "ah": 45, "al": 32, "rip": 4552273184, "r9": 140734542499840, "spl": 184,
    "ax": 11552, "fctrl": 895, "rax": 4552273184, "r11l": 70, "r10": 140734542498816, "r11": 582, "r11d": 582,
    "foseg": 0, "r11w": 582, "fs": 0, "ymm11": "n/a", "ymm10": "n/a", "ymm13": "n/a", "ymm12": "n/a", "ymm15": "n/a",
    "ymm14": "n/a", "sp": 57016, "si": 57048})
read_memory_response = "\xff"*0x40
read_stack_response = "\xff"*0x40
wait_response = "stopped"
execute_command_response = "inferior`main:\n-> 0x100000d20:  pushq  %rbp\n   0x100000d21:  movq   %rsp, %rbp\n   0x100000d24:  subq   $0x40, %rsp\n   0x100000d28:  movl   $0x0, -0x4(%rbp)\n   0x100000d2f:  movl   %edi, -0x8(%rbp)\n   0x100000d32:  movq   %rsi, -0x10(%rbp)\n   0x100000d36:  movl   $0x0, -0x14(%rbp)\n   0x100000d3d:  movq   $0x0, -0x20(%rbp)\n   0x100000d45:  cmpl   $0x1, -0x8(%rbp)\n   0x100000d4c:  jle    0x100000d94               ; main + 116\n   0x100000d52:  movq   -0x10(%rbp), %rax\n   0x100000d56:  movq   0x8(%rax), %rdi\n   0x100000d5a:  leaq   0x18a(%rip), %rsi         ; \"sleep\"\n   0x100000d61:  callq  0x100000ea0               ; symbol stub for: strcmp\n   0x100000d66:  cmpl   $0x0, %eax\n   0x100000d6b:  jne    0x100000d94               ; main + 116\n   0x100000d71:  leaq   0x179(%rip), %rdi         ; \"*** Sleeping for 5 seconds\\n\"\n   0x100000d78:  movb   $0x0, %al\n   0x100000d7a:  callq  0x100000e94               ; symbol stub for: printf\n   0x100000d7f:  movl   $0x5, %edi\n   0x100000d84:  movl   %eax, -0x24(%rbp)\n   0x100000d87:  callq  0x100000e9a               ; symbol stub for: sleep\n   0x100000d8c:  movl   %eax, -0x28(%rbp)\n   0x100000d8f:  jmpq   0x100000e88               ; main + 360\n   0x100000d94:  cmpl   $0x1, -0x8(%rbp)\n   0x100000d9b:  jle    0x100000dd6               ; main + 182\n   0x100000da1:  movq   -0x10(%rbp), %rax\n   0x100000da5:  movq   0x8(%rax), %rdi\n   0x100000da9:  leaq   0x15d(%rip), %rsi         ; \"loop\"\n   0x100000db0:  callq  0x100000ea0               ; symbol stub for: strcmp\n   0x100000db5:  cmpl   $0x0, %eax\n   0x100000dba:  jne    0x100000dd6               ; main + 182"
disassemble_response = execute_command_response

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
    adaptor.version = Mock(return_value='lldb-something')
    adaptor.state = Mock(return_value=state_response)
    adaptor.target = Mock(return_value=targets_response[0])
    adaptor._target = Mock(return_value=targets_response[0])
    adaptor.targets = Mock(return_value=targets_response)
    adaptor.read_registers = Mock(return_value=read_registers_response)
    adaptor.read_memory = Mock(return_value=read_memory_response)
    adaptor.read_stack = Mock(return_value=read_stack_response)
    adaptor.wait = Mock(return_value=wait_response)
    adaptor.execute_command = Mock(return_value=execute_command_response)
    adaptor.disassemble = Mock(return_value=disassemble_response)

    # start up a voltron server
    server = Server(plugin_mgr=pm, debugger=adaptor)
    server.start()

    time.sleep(0.1)

    # set up client
    client = Client()
    client.connect()

def teardown():
    server.stop()

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
    assert res.error_code == 0x1001

def test_front_end_bad_request():
    req = pm.api_plugins['version'].request_class()
    req.request = 'xxx'
    res = client.send_request(req)
    assert res.is_error
    assert res.error_code == 0x1002

def test_front_end_host_not_supported():
    req = pm.api_plugins['host_not_supported'].request_class()
    res = client.send_request(req)
    assert res.is_error
    assert res.error_code == 0x1003

def test_backend_version():
    res = pm.api_plugins['version'].request_class().dispatch()
    assert res.data['api_version'] == 1.0
    assert res.data['host_version'] == 'lldb-something'

def test_direct_version():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "version"
        }
    ))
    res = pm.api_plugins['version'].response_class(data)
    assert res.data['api_version'] == 1.0
    assert res.data['host_version'] == 'lldb-something'

def test_frontend_version():
    req = pm.api_plugins['version'].request_class()
    res = client.send_request(req)
    assert res.data['api_version'] == 1.0
    assert res.data['host_version'] == 'lldb-something'

def test_backend_state():
    res = pm.api_plugins['state'].request_class().dispatch()
    assert res.is_success
    assert res.data["state"] == "stopped"

def test_direct_state():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "state"
        }
    ))
    res = pm.api_plugins['state'].response_class(data)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_state():
    req = pm.api_plugins['state'].request_class()
    res = client.send_request(req)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_state_with_id():
    req = pm.api_plugins['state'].request_class()
    req.data['target_id'] = 0
    res = client.send_request(req)
    assert res.is_success
    assert res.state == "stopped"

def test_frontend_wait_timeout():
    req = pm.api_plugins['wait'].request_class(timeout=2)
    res = client.send_request(req)
    assert res.is_error

def test_backend_list_targets():
    res = pm.api_plugins['list_targets'].request_class().dispatch()
    assert res.is_success
    assert res.data["targets"] == targets_response

def test_direct_list_targets():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "list_targets"
        }
    ))
    res = pm.api_plugins['list_targets'].response_class(data=data)
    assert res.is_success
    assert res.data["targets"] == targets_response

def test_frontend_list_targets():
    req = pm.api_plugins['list_targets'].request_class()
    res = client.send_request(req)
    assert res.is_success
    assert res.data["targets"] == targets_response

def test_backend_read_registers():
    res = pm.api_plugins['read_registers'].request_class().dispatch()
    assert res.is_success
    assert res.data["registers"] == read_registers_response

def test_direct_read_registers():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "read_registers"
        }
    ))
    res = pm.api_plugins['read_registers'].response_class(data)
    assert res.is_success
    assert res.data["registers"] == read_registers_response

def test_frontend_read_registers():
    req = pm.api_plugins['read_registers'].request_class()
    res = client.send_request(req)
    assert res.is_success
    assert res.data["registers"] == read_registers_response

def test_backend_read_memory():
    res = pm.api_plugins['read_memory'].request_class(address=0x1000, length=0x40).dispatch()
    assert res.is_success
    assert res.memory == read_memory_response

def test_direct_read_memory():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "read_memory",
            "data": {
                "target_id": 0,
                "address": 0x1000,
                "length": 0x40
            }
        }
    ))
    res = pm.api_plugins['read_memory'].response_class(data)
    assert res.is_success
    assert res.memory == read_memory_response

def test_frontend_read_memory():
    req = pm.api_plugins['read_memory'].request_class(0x1000, 0x40)
    res = client.send_request(req)
    assert res.is_success
    assert res.memory == read_memory_response

def test_backend_read_stack():
    res = pm.api_plugins['read_stack'].request_class(length=0x40).dispatch()
    assert res.is_success
    assert res.memory == read_stack_response

def test_direct_read_stack():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "read_stack",
            "data": {
                "target_id": 0,
                "length": 0x40
            }
        }
    ))
    res = pm.api_plugins['read_stack'].response_class(data)
    assert res.is_success
    assert res.memory == read_stack_response

def test_frontend_read_stack():
    req = pm.api_plugins['read_stack'].request_class(0x40)
    res = client.send_request(req)
    assert res.is_success
    assert res.memory == read_stack_response

def test_backend_execute_command():
    res = pm.api_plugins['execute_command'].request_class("reg read").dispatch()
    assert res.is_success
    assert res.output == execute_command_response

def test_direct_execute_command():
    data = make_direct_request(json.dumps(
        {
            "type":         "request",
            "request":      "execute_command",
            "data": {
                "command": "reg read"
            }
        }
    ))
    res = pm.api_plugins['execute_command'].response_class(data)
    assert res.is_success
    assert res.output == execute_command_response

def test_frontend_execute_command():
    req = pm.api_plugins['execute_command'].request_class("reg read")
    res = client.send_request(req)
    assert res.is_success
    assert res.output == execute_command_response

def test_backend_disassemble():
    res = pm.api_plugins['disassemble'].request_class(count=16).dispatch()
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
    res = pm.api_plugins['disassemble'].response_class(data)
    assert res.is_success
    assert res.disassembly == disassemble_response

def test_frontend_disassemble():
    req = pm.api_plugins['disassemble'].request_class(count=16)
    res = client.send_request(req)
    assert res.is_success
    assert res.disassembly == disassemble_response
