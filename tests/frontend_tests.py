"""
These tests load an inferior into an LLDB instance and then issue API requests
using the client.

Tests:
Client -> Server -> LLDBAdaptor

Using an instantiated SBDebugger instance
"""

import tempfile
import sys
import json
import time
import logging
import subprocess

from mock import Mock
from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import PluginManager, DebuggerAdaptorPlugin

import platform
if platform.system() == 'Darwin':
    sys.path.append("/Applications/Xcode.app/Contents/SharedFrameworks/LLDB.framework/Resources/Python")

import lldb

from common import *

log = logging.getLogger(__name__)

def setup():
    global server, client, target, pm, adaptor, methods

    log.info("setting up API tests")

    # set up voltron
    voltron.setup_env()
    pm = PluginManager()
    plugin = pm.debugger_plugin_for_host('lldb')
    adaptor = plugin.adaptor_class()
    voltron.debugger = adaptor

    # start up a voltron server
    server = Server(plugin_mgr=pm, debugger=adaptor)
    server.start()

    time.sleep(0.1)

    # set up client
    client = Client()
    client.connect()

    # compile and load the test inferior
    subprocess.call("cc -o tests/inferior tests/inferior.c", shell=True)
    target = adaptor.host.CreateTargetWithFileAndArch("tests/inferior", lldb.LLDB_ARCH_DEFAULT)

def teardown():
    server.stop()

def test_state_no_target():
    req = pm.api_plugins['state'].request_class()
    res = client.send_request(req)
    assert res.is_error
    assert res.error_code == 4101

def test_state_stopped():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['state'].request_class()
    res = client.send_request(req)
    assert res.status == 'success'
    assert res.state == "stopped"
    target.process.Destroy()

def test_wait_timeout():
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['wait'].request_class(timeout=1, state_changes=["invalid"])
    res = client.send_request(req)
    assert res.status == 'error'
    assert res.error_code == 0x1004
    target.process.Destroy()

def test_list_targets():
    req = pm.api_plugins['list_targets'].request_class()
    res = client.send_request(req)
    assert res.status == 'success'
    t = res.data["targets"][0]
    assert t["id"] == 0
    assert t["arch"] == "x86_64"
    assert t["file"].endswith("inferior")

def test_read_registers():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['read_registers'].request_class()
    res = client.send_request(req)
    assert res.status == 'success'
    assert len(res.data["registers"]) > 0
    assert res.data["registers"]['rip'] != 0
    target.process.Destroy()

def test_read_memory():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['read_registers'].request_class()
    res = client.send_request(req)
    req = pm.api_plugins['read_memory'].request_class(address=res.registers['rip'], length=0x40)
    res = client.send_request(req)
    assert res.status == 'success'
    assert len(res.memory) > 0
    target.process.Destroy()

def test_read_stack():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['read_stack'].request_class(length=0x40)
    res = client.send_request(req)
    assert res.status == 'success'
    assert len(res.memory) > 0
    target.process.Destroy()

def test_execute_command():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['execute_command'].request_class("reg read")
    res = client.send_request(req)
    assert res.status == 'success'
    assert len(res.output) > 0
    assert 'rax' in res.output
    target.process.Destroy()

def test_disassemble():
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())
    process = target.LaunchSimple(None, None, os.getcwd())
    req = pm.api_plugins['disassemble'].request_class(count=16)
    res = client.send_request(req)
    assert res.status == 'success'
    assert len(res.disassembly) > 0
    assert 'push' in res.disassembly
    target.process.Destroy()

