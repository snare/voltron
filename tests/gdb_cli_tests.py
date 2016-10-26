"""
Tests that test voltron in the gdb cli driver

Tests:
Client -> Server -> GDBAdaptor

Inside a GDB instance
"""

from __future__ import print_function

import tempfile
import sys
import json
import time
import logging
import pexpect
import os
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

    log.info("setting up GDB CLI tests")

    voltron.setup_env()

    # compile test inferior
    pexpect.run("cc -o tests/inferior tests/inferior.c")

    # start debugger
    start_debugger()


def teardown():
    read_data()
    p.terminate(True)


def start_debugger(do_break=True):
    global p, client
    p = pexpect.spawn('gdb')
    p.sendline("python import sys;sys.path.append('/home/travis/virtualenv/python3.5.0/lib/python3.5/site-packages')")
    p.sendline("python import sys;sys.path.append('/home/travis/virtualenv/python3.4.3/lib/python3.4/site-packages')")
    p.sendline("python import sys;sys.path.append('/home/travis/virtualenv/python3.3.6/lib/python3.3/site-packages')")
    p.sendline("python import sys;sys.path.append('/home/travis/virtualenv/python2.7.10/lib/python2.7/site-packages')")
    p.sendline("source voltron/entry.py")
    p.sendline("file tests/inferior")
    p.sendline("set disassembly-flavor intel")
    p.sendline("voltron init")
    if do_break:
        p.sendline("b main")
    p.sendline("run loop")
    read_data()

    time.sleep(5)

    client = Client()


def stop_debugger():
    # p.sendline("kill")
    read_data()
    p.terminate(True)


def read_data():
    try:
        while True:
            data = p.read_nonblocking(size=64, timeout=1)
            print(data.decode('UTF-8'), end='')
    except:
        pass


def restart_debugger(do_break=True):
    stop_debugger()
    start_debugger(do_break)


def test_bad_request():
    req = client.create_request('version')
    req.request = 'xxx'
    res = client.send_request(req)
    assert res.is_error
    assert res.code == 0x1002


def test_version():
    req = client.create_request('version')
    res = client.send_request(req)
    assert res.api_version == 1.1
    assert 'gdb' in res.host_version


def test_registers():
    global registers
    read_data()
    res = client.perform_request('registers')
    registers = res.registers
    assert res.status == 'success'
    assert len(registers) > 0
    assert registers['rip'] != 0


def test_memory():
    res = client.perform_request('memory', address=registers['rip'], length=0x40)
    assert res.status == 'success'
    assert len(res.memory) > 0


def test_state_stopped():
    res = client.perform_request('state')
    assert res.is_success
    assert res.state == "stopped"


def test_targets():
    res = client.perform_request('targets')
    assert res.is_success
    assert res.targets[0]['state'] == "stopped"
    assert res.targets[0]['arch'] == "x86_64"
    assert res.targets[0]['id'] == 0
    assert res.targets[0]['file'].endswith('tests/inferior')


def test_stack():
    res = client.perform_request('stack', length=0x40)
    assert res.status == 'success'
    assert len(res.memory) > 0


def test_command():
    res = client.perform_request('command', command="info reg")
    assert res.status == 'success'
    assert len(res.output) > 0
    assert 'rax' in res.output


def test_disassemble():
    res = client.perform_request('disassemble', count=0x20)
    assert res.status == 'success'
    assert len(res.disassembly) > 0
    assert 'DWORD' in res.disassembly


def test_backtrace():
    res = client.perform_request('backtrace')
    print(res)
    assert res.is_success
    assert res.frames[0]['name'] == "main"
    assert res.frames[0]['index'] == 0


def test_write_memory():
    value = six.b("AAAAAAAA")
    res = client.perform_request('write_memory', address=registers['rsp'], value=value)
    assert res.is_success
    res = client.perform_request('memory', address=registers['rsp'], length=len(value))
    assert res.memory == value
