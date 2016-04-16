"""
Tests that test voltron in the lldb cli driver

Tests:
Client -> Server -> LLDBAdaptor

Inside an LLDB CLI driver instance
"""
from __future__ import print_function

import tempfile
import sys
import json
import time
import logging
import pexpect
import os
import tempfile
import six

from mock import Mock
from nose.tools import *

import voltron
from voltron.core import *
from voltron.api import *
from voltron.plugin import PluginManager, DebuggerAdaptorPlugin

from .common import *

log = logging.getLogger('tests')

p = None
client = None


def setup():
    global p, client, pm

    log.info("setting up LLDB CLI tests")

    voltron.setup_env()

    # compile test inferior
    pexpect.run("cc -o tests/inferior tests/inferior.c")

    # start debugger
    start_debugger()
    time.sleep(5)


def teardown():
    read_data()
    p.terminate(True)
    time.sleep(2)


def start_debugger(do_break=True):
    global p, client

    if sys.platform == 'darwin':
        p = pexpect.spawn('lldb')
    else:
        p = pexpect.spawn('lldb-3.4')

        # for travis
        (f, tmpname) = tempfile.mkstemp('.py')
        os.write(f, six.b('\n'.join([
            "import sys",
            "sys.path.append('/home/travis/virtualenv/python3.5.0/lib/python3.5/site-packages')",
            "sys.path.append('/home/travis/virtualenv/python3.4.3/lib/python3.4/site-packages')",
            "sys.path.append('/home/travis/virtualenv/python3.3.6/lib/python3.3/site-packages')",
            "sys.path.append('/home/travis/virtualenv/python2.7.10/lib/python2.7/site-packages')"])))
        p.sendline("command script import {}".format(tmpname))

    print("pid == {}".format(p.pid))
    p.sendline("settings set target.x86-disassembly-flavor intel")
    p.sendline("command script import voltron/entry.py")
    time.sleep(2)
    p.sendline("file tests/inferior")
    time.sleep(2)
    p.sendline("voltron init")
    time.sleep(1)
    p.sendline("process kill")
    p.sendline("break delete 1")
    if do_break:
        p.sendline("b main")
    p.sendline("run loop")
    read_data()
    client = Client()


def stop_debugger():
    p.terminate(True)


def read_data():
    try:
        while True:
            data = p.read_nonblocking(size=64, timeout=1)
            print(data.decode('UTF-8'), end='')
    except:
        pass


def restart(do_break=True):
    # stop_debugger()
    # start_debugger(do_break)
    p.sendline("process kill")
    p.sendline("break delete -f")
    if do_break:
        p.sendline("b main")
    p.sendline("run loop")


def test_bad_request():
    req = client.create_request('version')
    req.request = 'xxx'
    res = client.send_request(req)
    assert res.is_error
    assert res.code == 0x1002
    time.sleep(2)


def test_version():
    req = client.create_request('version')
    res = client.send_request(req)
    assert res.api_version == 1.1
    assert 'lldb' in res.host_version


def test_registers():
    global registers
    restart()
    time.sleep(1)
    read_data()
    res = client.perform_request('registers')
    registers = res.registers
    assert res.status == 'success'
    assert len(registers) > 0
    if 'rip' in registers:
        assert registers['rip'] != 0
    else:
        assert registers['eip'] != 0


def test_memory():
    restart()
    time.sleep(1)
    res = client.perform_request('memory', address=registers['rip'], length=0x40)
    assert res.status == 'success'
    assert len(res.memory) > 0


def test_state_stopped():
    restart()
    time.sleep(1)
    res = client.perform_request('state')
    assert res.is_success
    assert res.state == "stopped"


def test_targets():
    restart()
    time.sleep(1)
    res = client.perform_request('targets')
    assert res.is_success
    assert res.targets[0]['state'] == "stopped"
    assert res.targets[0]['arch'] == "x86_64"
    assert res.targets[0]['id'] == 0
    assert res.targets[0]['file'].endswith('tests/inferior')


def test_stack():
    restart()
    time.sleep(1)
    res = client.perform_request('stack', length=0x40)
    assert res.status == 'success'
    assert len(res.memory) > 0


def test_command():
    restart()
    time.sleep(1)
    res = client.perform_request('command', command="reg read")
    assert res.status == 'success'
    assert len(res.output) > 0
    assert 'rax' in res.output


def test_disassemble():
    restart()
    time.sleep(1)
    res = client.perform_request('disassemble', count=0x20)
    assert res.status == 'success'
    assert len(res.disassembly) > 0
    assert 'push' in res.disassembly


def test_dereference():
    restart()
    time.sleep(1)
    res = client.perform_request('registers')
    res = client.perform_request('dereference', pointer=res.registers['rsp'])
    assert res.status == 'success'
    assert res.output[0][0] == 'pointer'
    assert 'start' in res.output[-1][1] or 'main' in res.output[-1][1]


def test_breakpoints():
    restart(True)
    time.sleep(1)
    res = client.perform_request('breakpoints')
    assert res.status == 'success'
    # assert len(res.breakpoints) == 1
    assert res.breakpoints[0]['one_shot'] == False
    assert res.breakpoints[0]['enabled']
    # assert res.breakpoints[0]['id'] == 1
    assert res.breakpoints[0]['hit_count'] > 0
    assert res.breakpoints[0]['locations'][0]['name'] == "inferior`main"


# def test_multi():
#     global r1, r2
#     restart(True)
#     time.sleep(1)
#     r1, r2 = None, None

#     def send_req():
#         global r1, r2
#         r1, r2 = client.send_requests(api_request('targets', block=True), api_request('registers', block=True))
#         print "sent requests"

#     t = threading.Thread(target=send_req)
#     t.start()
#     time.sleep(5)
#     p.sendline("stepi")
#     time.sleep(5)
#     t.join()
#     print r1
#     print r2
#     assert r1.is_success
#     assert r1.targets[0]['state'] == "stopped"
#     assert r1.targets[0]['arch'] == "x86_64"
#     assert r1.targets[0]['id'] == 0
#     assert r1.targets[0]['file'].endswith('tests/inferior')
#     assert r2.status == 'success'
#     assert len(r2.registers) > 0
#     assert r2.registers['rip'] != 0


def test_capabilities():
    restart(True)
    res = client.perform_request('version')
    assert res.capabilities == ['async']


def test_backtrace():
    restart(True)
    time.sleep(1)
    res = client.perform_request('backtrace')
    print(res)
    assert res.frames[0]['name'] == "inferior`main + 0"
    assert res.frames[0]['index'] == 0
