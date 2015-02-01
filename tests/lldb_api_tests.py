"""
Tests that exercise the LLDB backend directly by loading an inferior and then
poking at it with the LLDBAdaptor class.

Tests:
LLDBAdaptor
"""

import tempfile
import sys
import json
import time
import logging
import subprocess
import threading

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

voltron.setup_env()

log = logging.getLogger('tests')

def setup():
    global adaptor, dbg, target

    log.info("setting up LLDB API tests")

    # create an LLDBAdaptor
    pm = PluginManager()
    plugin = pm.debugger_plugin_for_host('lldb')
    adaptor = plugin.adaptor_class()

    # compile and load the test inferior
    subprocess.call("cc -o tests/inferior tests/inferior.c", shell=True)
    target = adaptor.host.CreateTargetWithFileAndArch("tests/inferior", lldb.LLDB_ARCH_DEFAULT)
    main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())

def teardown():
    time.sleep(2)

def test_version():
    assert 'lldb' in adaptor.version()

def test_state_invalid():
    try:
        adaptor.state()
        exception = False
    except NoSuchTargetException:
        exception = True
    except:
        exception = False
    assert exception

def test_targets_not_running():
    t = adaptor.targets()[0]
    assert t["state"] == "invalid"
    assert t["arch"] == "x86_64"
    assert t["id"] == 0
    assert len(t["file"]) > 0
    assert 'inferior' in t["file"]

def test_targets_stopped():
    process = target.LaunchSimple(None, None, os.getcwd())
    t = adaptor.targets()[0]
    assert t["state"] == "stopped"
    process.Destroy()

def test_registers():
    process = target.LaunchSimple(None, None, os.getcwd())
    regs = adaptor.registers()
    assert regs != None
    assert len(regs) > 0
    assert regs['rip'] != 0
    process.Destroy()

def test_stack_pointer():
    process = target.LaunchSimple(None, None, os.getcwd())
    sp = adaptor.stack_pointer()
    assert sp != 0
    process.Destroy()

def test_program_counter():
    process = target.LaunchSimple(None, None, os.getcwd())
    pc_name, pc = adaptor.program_counter()
    assert pc != 0
    process.Destroy()

def test_memory():
    process = target.LaunchSimple(None, None, os.getcwd())
    regs = adaptor.registers()
    mem = adaptor.memory(address=regs['rip'], length=0x40)
    assert len(mem) == 0x40
    process.Destroy()

def test_stack():
    process = target.LaunchSimple(None, None, os.getcwd())
    stack = adaptor.stack(length=0x40)
    assert len(stack) == 0x40
    process.Destroy()

def test_disassemble():
    process = target.LaunchSimple(None, None, os.getcwd())
    output = adaptor.disassemble(count=0x20)
    assert len(output) > 0
    process.Destroy()

def test_command():
    process = target.LaunchSimple(None, None, os.getcwd())
    output = adaptor.command("reg read")
    assert len(output) > 0
    assert 'rax' in output
    process.Destroy()

def test_dereference_main():
    process = target.LaunchSimple(None, None, os.getcwd())
    regs = adaptor.registers()
    output = adaptor.dereference(regs['rip'])
    assert ('symbol', 'main + 0x0') in output
    process.Destroy()

def test_dereference_rsp():
    process = target.LaunchSimple(None, None, os.getcwd())
    regs = adaptor.registers()
    output = adaptor.dereference(regs['rsp'])
    assert ('symbol', 'start + 0x1') in output
    process.Destroy()

def test_dereference_string():
    process = target.LaunchSimple(None, None, os.getcwd())
    regs = adaptor.registers()
    output = adaptor.dereference(regs['rsp']+0x20)
    assert 'inferior' in list(output[-1])[-1]
    process.Destroy()

def test_breakpoints():
    process = target.LaunchSimple(None, None, os.getcwd())
    bps = adaptor.breakpoints()
    assert len(bps) == 1
    assert bps[0]['one_shot'] == False
    assert bps[0]['enabled']
    assert bps[0]['id'] == 1
    assert bps[0]['hit_count'] > 0
    assert bps[0]['locations'][0]['name'] == "inferior`main"
    process.Destroy()