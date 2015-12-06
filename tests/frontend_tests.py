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

try:
    import lldb

    from .common import *

    log = logging.getLogger("tests")

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
        server = Server()
        # import pdb;pdb.set_trace()
        server.start()

        time.sleep(0.1)

        # set up client
        client = Client()

        # compile and load the test inferior
        subprocess.call("cc -o tests/inferior tests/inferior.c", shell=True)
        target = adaptor.host.CreateTargetWithFileAndArch("tests/inferior", lldb.LLDB_ARCH_DEFAULT)
        main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())

    def teardown():
        server.stop()
        time.sleep(5)

    def test_state_no_target():
        req = api_request('state')
        res = client.send_request(req)
        assert res.is_error
        assert res.code == 4101

    def test_state_stopped():
        process = target.LaunchSimple(None, None, os.getcwd())
        req = api_request('state')
        res = client.send_request(req)
        assert res.status == 'success'
        assert res.state == "stopped"
        target.process.Destroy()

    def test_targets():
        req = api_request('targets')
        res = client.send_request(req)
        assert res.status == 'success'
        t = res.targets[0]
        assert t["id"] == 0
        assert t["arch"] == "x86_64"
        assert t["file"].endswith("inferior")

    def test_registers():
        process = target.LaunchSimple(None, None, os.getcwd())
        req = api_request('registers')
        res = client.send_request(req)
        assert res.status == 'success'
        assert len(res.registers) > 0
        assert res.registers['rip'] != 0
        target.process.Destroy()

    def test_memory():
        process = target.LaunchSimple(None, None, os.getcwd())
        res = client.perform_request('registers')
        rsp = res.registers['rsp']
        res = client.perform_request('memory', address=rsp, length=0x40)
        assert res.status == 'success'
        assert len(res.memory) > 0
        res = client.perform_request('memory', address=rsp, length=0x40, deref=True)
        assert res.status == 'success'
        assert len(res.deref) > 0
        target.process.Destroy()

    def test_stack():
        process = target.LaunchSimple(None, None, os.getcwd())
        req = api_request('stack', length=0x40)
        res = client.send_request(req)
        assert res.status == 'success'
        assert len(res.memory) > 0
        target.process.Destroy()

    def test_command():
        process = target.LaunchSimple(None, None, os.getcwd())
        req = api_request('command', command="reg read")
        res = client.send_request(req)
        assert res.status == 'success'
        assert len(res.output) > 0
        assert 'rax' in res.output
        target.process.Destroy()

    def test_disassemble():
        process = target.LaunchSimple(None, None, os.getcwd())
        req = api_request('disassemble', count=16)
        res = client.send_request(req)
        assert res.status == 'success'
        assert len(res.disassembly) > 0
        assert 'push' in res.disassembly
        target.process.Destroy()

    def test_dereference():
        process = target.LaunchSimple(None, None, os.getcwd())
        res = client.perform_request('registers')
        res = client.perform_request('dereference', pointer=res.registers['rsp'])
        assert res.status == 'success'
        assert res.output[0][0] == 'pointer'
        assert res.output[-1][1] == 'start + 0x1'
        target.process.Destroy()

    def test_breakpoints():
        process = target.LaunchSimple(None, None, os.getcwd())
        res = client.perform_request('breakpoints')
        assert res.status == 'success'
        assert len(res.breakpoints) == 1
        assert res.breakpoints[0]['one_shot'] == False
        assert res.breakpoints[0]['enabled']
        assert res.breakpoints[0]['id'] == 1
        assert res.breakpoints[0]['hit_count'] > 0
        assert res.breakpoints[0]['locations'][0]['name'] == "inferior`main"
        target.process.Destroy()

    def test_multi_request():
        process = target.LaunchSimple(None, None, os.getcwd())
        reg_res, dis_res = client.send_requests(api_request('registers'),
                                                api_request('disassemble', count=16))
        assert reg_res.status == 'success'
        assert len(reg_res.registers) > 0
        assert reg_res.registers['rip'] != 0
        assert dis_res.status == 'success'
        assert len(dis_res.disassembly) > 0
        assert 'push' in dis_res.disassembly
        target.process.Destroy()

except:
    print("No LLDB")