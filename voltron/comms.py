import os
import logging
import socket
import select
try:
    import Queue
except:
    import queue as Queue
import time
import pickle
import threading
import logging
import logging.config

from .common import *
from .env import *
import voltron.cmd

READ_MAX = 0xFFFF

queue = Queue.Queue()

log = configure_logging()

#
# Classes shared between client and server
#

# Base socket class
class BaseSocket(object):
    def fileno(self):
        return self.sock.fileno()

    def close(self):
        self.sock.close()

    def send(self, buf):
        self.sock.send(buf)


class SocketDisconnected(Exception): pass


#
# Client-side classes
#

# Socket to register with the server and receive messages, calls view's render() method when a message comes in
class Client(BaseSocket):
    def __init__(self, view=None, config={}):
        self.view = view
        self.config = config
        self.reg_info = None
        self.sock = None
        self.do_connect()

    def do_connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        success = False
        while not success:
            try:
                self.sock.connect(VOLTRON_SOCKET)
                success = True
                self.register()
            except Exception as e:
                if self.view:
                    self.view.render(error="Failed connecting to server:" + str(e))
                    time.sleep(1)
                else:
                    raise e

    def register(self):
        log.debug('Client {} registering with config: {}'.format(self, str(self.config)))
        msg = {'msg_type': 'register', 'config': self.config}
        log.debug('Sending: ' + str(msg))
        self.send(pickle.dumps(msg))

    def recv(self):
        return self.sock.recv(READ_MAX)

    def read(self):
        data = self.recv()
        if len(data) > 0:
            msg = None
            try:
                msg = pickle.loads(data)
                log.debug('Received message: ' + str(msg))
            except Exception as e:
                log.error('Exception parsing message: ' + str(e))
                log.error('Invalid message: ' + data)

            if msg and self.view:
                self.view.render(msg)
        else:
            log.debug('Empty read')
            raise SocketDisconnected("socket closed")


# Used by calculon
class InteractiveClient(Client):
    def query(self, msg):
        self.send(pickle.dumps(msg))
        resp = self.recv()
        if len(resp) > 0:
            return pickle.loads(resp)


#
# Server-side classes
#

# Wrapper for a ServerThread to run in the context of a debugger host. Responsible for:
# - Collecting clients (populated by ServerThread)
# - Providing summaries of connected clients to the host DebuggerCommand or Console
# - Collecting data from a DebuggerHelper and sending out updates
# - Responding to requests from interactive clients
# - Handling push updates from proxy clients
class Server (object):
    def __init__(self):
        self._clients = []
        self.exit_out, self.exit_in = os.pipe()
        self.base_helper = None
        self.helper = None

    def start(self):
        log.debug("Starting server thread")
        self.thread = ServerThread(self, self._clients, self.exit_out)
        self.thread.start()

    def stop(self):
        log.debug("Stopping server thread")
        os.write(self.exit_in, chr(0))
        self.thread.join(10)

    @property
    def clients(self):
        return self._clients

    def client_summary(self):
        return [str(c) + ': ' + c.registration['config']['type'] for c in self._clients]

    def refresh_helper(self):
        # if we don't have a helper, or the one we have is for the wrong architecture, get a new one
        if self.helper == None or self.helper != None and self.helper.get_arch() not in self.helper.archs:
            self.helper = self.base_helper.helper()

    def update_clients(self):
        log.debug("Updating clients")

        # Make sure we have a target
        if not self.base_helper.has_target():
            return

        # Make sure we have a helper
        self.refresh_helper()

        # Process updates for registered clients
        log.debug("Processing updates")
        for client in filter(lambda c: c.registration['config']['update_on'] == 'stop', self._clients):
            event = {'msg_type': 'update', 'arch': self.helper.arch_group}
            if client.registration['config']['type'] == 'cmd':
                event['data'] = self.helper.get_cmd_output(client.registration['config']['cmd'])
            elif client.registration['config']['type'] == 'register':
                event['data'] = {'regs': self.helper.get_registers(), 'inst': self.helper.get_next_instruction()}
            elif client.registration['config']['type'] == 'disasm':
                event['data'] = self.helper.get_disasm()
            elif client.registration['config']['type'] == 'stack':
                event['data'] = {'data': self.helper.get_stack(), 'sp': self.helper.get_sp()}
            elif client.registration['config']['type'] == 'bt':
                event['data'] = self.helper.get_backtrace()

            try:
                client.send_event(event)
            except socket.error:
                self.server.purge_client(client)

    def handle_push_update(self, client, msg):
        log.debug('Got a push update from client {} of type {} with data: {}'.format(self, msg['update_type'], str(msg['data'])))
        event = {'msg_type': 'update', 'data': msg['data']}
        for c in self._clients:
            if c.registration != None and c.registration['config']['type'] == msg['update_type']:
                c.send_event(event)
        client.send_event(pickle.dumps({'msg_type': 'ack'}))

    def handle_interactive_query(self, client, msg):
        log.debug('Got an interactive query from client {} of type {}'.format(self, msg['query']))
        resp = {'value': None}
        if msg['query'] == 'get_register':
            reg = msg['register']
            registers = self.helper.get_registers()
            if reg in registers:
                resp['value'] = registers[reg]
        elif msg['query'] == 'get_memory':
            try:
                start = int(msg['start'])
                end = int(msg['end'])
                length = end - start
                assert(length > 0)
                resp['value'] = self.helper.get_memory(start, length)
            except:
                pass
        client.send_event(resp)


# Wrapper for a ServerThread to run in standalone mode for debuggers without python support
class StandaloneServer(Server):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('server', help='standalone server for debuggers without python support')
        sp.set_defaults(func=StandaloneServer)

    def __init__(self, args={}, loaded_config={}):
        self.args = args

    def run(self):
        log.debug("Running standalone server")
        self.start()
        while True:
            time.sleep(1)


# Thread spun off when the server is started to listen for incoming client connections
class ServerThread(threading.Thread):
    def __init__(self, server, clients, exit_pipe):
        self.server = server
        self.clients = clients
        self.exit_pipe = exit_pipe
        threading.Thread.__init__(self)

    def run(self):
        # Make sure there's no left over socket
        try:
            os.remove(VOLTRON_SOCKET)
        except:
            pass

        # Create a server socket instance
        serv = ServerSocket(VOLTRON_SOCKET)
        self.lock = threading.Lock()

        # Main event loop
        running = True
        while running:
            _rfds = [serv, self.exit_pipe] + self.clients
            rfds, _, _ = select.select(_rfds, [], [])
            for i in rfds:
                if i == serv:
                    client = i.accept()
                    client.server = self.server
                    self.clients.append(client)
                elif i == self.exit_pipe:
                    # Flush the pipe
                    os.read(self.exit_pipe, 1)
                    running = False
                    break
                else:
                    try:
                        i.read()
                    except socket.error:
                        self.purge_client(i)
                    except SocketDisconnected:
                        self.purge_client(i)
        # Clean up
        for client in self.clients:
            client.close()
        os.close(self.exit_pipe)
        serv.close()
        try:
            os.remove(VOLTRON_SOCKET)
        except:
            pass

    def purge_client(self, client):
        client.close()
        self.clients.remove(client)


# Socket for talking to an individual client, collected by Server/ServerThread
class ClientHandler(BaseSocket):
    def __init__(self, sock):
        self.sock = sock
        self.registration = None

    def read(self):
        data = self.sock.recv(READ_MAX)
        if len(data.strip()):
            # receive message
            try:
                msg = pickle.loads(data)
                log.debug('Received msg: ' + str(msg))
            except Exception as e:
                log.error('Exception: ' + str(e))
                log.error('Invalid message data: ' + str(data))
                return

            # store registration or dispatch message to server
            if msg['msg_type'] == 'register':
                log.debug('Registering client {} with config: {}'.format(self, str(msg['config'])))
                self.registration = msg
            elif msg['msg_type'] == 'push_update':
                self.server.handle_push_update(self, msg)
            elif msg['msg_type'] == 'interactive':
                self.server.handle_interactive_query(self, msg)
            else:
                log.error('Invalid message type: ' + msg['msg_type'])
        else:
            raise SocketDisconnected("socket closed")

    def send_event(self, event):
        log.debug('Sending event to client {}: {}'.format(self, event))
        self.send(pickle.dumps(event))


# Main server socket for accept()s
class ServerSocket(BaseSocket):
    def __init__(self, sockfile):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(sockfile)
        self.sock.listen(1)

    def accept(self):
        pair = self.sock.accept()
        if pair is not None:
            sock, addr = pair
            try:
                # TODO read some bytes, parse a header and dispatch to a
                # different client type
                return ClientHandler(sock)
            except Exception as e:
                log.error("Exception handling accept: " + str(e))
