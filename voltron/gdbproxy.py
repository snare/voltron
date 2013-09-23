import asyncore
import logging
import socket
import struct
try:
    import cPickle as pickle
except ImportError:
    import pickle

from .comms import _sock, READ_MAX
from .common import *

log = configure_logging()

# This class is called from the command line by GDBv6's stop-hook. The dumped registers and stack are collected,
# parsed and sent to the voltron standalone server, which then sends the updates out to any registered clients.
# I hate that this exists. Fuck GDBv6.
class GDB6Proxy (asyncore.dispatcher):
    REGISTERS = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cs','ds','es','fs','gs','ss']

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('gdb6proxy', help='import a dump from GDBv6 and send it to the server')
        sp.add_argument('type', action='store', help='the type to proxy - reg or stack')
        sp.set_defaults(func=GDB6Proxy)

    def __init__(self, args={}, loaded_config={}):
        global log
        asyncore.dispatcher.__init__(self)
        self.args = args
        if not args.debug:
            log.setLevel(logging.WARNING)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connect(_sock())

    def run(self):
        asyncore.loop()

    def handle_connect(self):
        if self.args.type == "reg":
            event = self.read_registers()
        elif self.args.type == "stack":
            event = self.read_stack()
        else:
            log.error("Invalid proxy type")
        log.debug("Pushing update to server")
        log.debug(str(event))
        self.send(pickle.dumps(event))

    def handle_read(self):
        data = self.recv(READ_MAX)
        msg = pickle.loads(data)
        if msg['msg_type'] != 'ack':
            log.error("Did not get ack: " + str(msg))
        self.close()

    def read_registers(self):
        log.debug("Parsing register data")
        data = {}
        for reg in GDB6Proxy.REGISTERS:
            try:
                with open('/tmp/voltron.reg.'+reg, 'r+b') as f:
                    if reg in ['eflags','cs','ds','es','fs','gs','ss']:
                        (val,) = struct.unpack('<L', f.read())
                    else:
                        (val,) = struct.unpack('<Q', f.read())
                data[reg] = val
            except Exception as e:
                log.warning("Exception reading register {}: {}".format(reg, str(e)))
                data[reg] = '<fail>'
        data['rflags'] = data['eflags']
        event = {'msg_type': 'push_update', 'update_type': 'register', 'data': data}
        return event

    def read_stack(self):
        log.debug("Parsing stack data")
        with open('/tmp/voltron.stack', 'r+b') as f:
            data = f.read()
        with open('/tmp/voltron.reg.rsp', 'r+b') as f:
            (rsp,) = struct.unpack('<Q', f.read())
        event = {'msg_type': 'push_update', 'update_type': 'stack', 'data': {'sp': rsp, 'data': data}}
        return event

    def cleanup(self):
        pass
