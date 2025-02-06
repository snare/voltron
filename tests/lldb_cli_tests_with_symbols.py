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
    pexpect.run("cc -g -o tests/inferior tests/inferior.c")

    # start debugger
    start_debugger()
    time.sleep(10)


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


def test_source_location():
    restart()
    time.sleep(1)
    res = client.perform_request('source_location', address=registers['rip'])
    assert res.status == 'success'
    assert not res.output is None
    file, line = res.output
    assert os.path.basename(file) == 'inferior.c'
    assert line == 12

