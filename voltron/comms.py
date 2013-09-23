import os
import logging
import socket
import asyncore
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

READ_MAX = 0xFFFF

def _sock():
    if "VOLTRON_SOCKET" in os.environ:
        return os.getenv("VOLTRON_SOCKET")
    else:
        d = VOLTRON_DIR
        if not os.path.exists(d):
            os.mkdir(d, 448)
        return os.path.join(d, "voltron.sock")

queue = Queue.Queue()
clients = []

log = configure_logging()

# Socket to register with the server and receive messages, calls view's render() method when a message comes in
class Client (asyncore.dispatcher):
    def __init__(self, view=None, config={}):
        asyncore.dispatcher.__init__(self)
        self.view = view
        self.config = config
        self.reg_info = None
        self.do_connect()

    def do_connect(self):
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        success = False
        while not success:
            try:
                self.connect(_sock())
                success = True
                self.register()
            except Exception as e:
                self.view.render(error="Failed connecting to server:" + str(e))
                time.sleep(1)

    def register(self):
        log.debug('Client {} registering with config: {}'.format(self, str(self.config)))
        msg = {'msg_type': 'register', 'config': self.config}
        log.debug('Sending: ' + str(msg))
        self.send(pickle.dumps(msg))

    def handle_read(self):
        data = self.recv(READ_MAX)
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

    def handle_close(self):
        self.close()
        self.do_connect()

    def writable(self):
        return False


# Wrapper for a ServerThread to run in the context of a debugger host
class Server (object):
    def start(self):
        log.debug("Starting server thread")
        self.thread = ServerThread()
        self.thread.start()

    def stop(self):
        log.debug("Stopping server thread")
        self.thread.set_should_exit(True)
        self.thread.join(10)

    def enqueue_event(self, client, event):
        queue.put((client, event))


# Wrapper for a ServerThread to run in standalone mode for debuggers without python support
class StandaloneServer (Server):
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

    def cleanup(self):
        self.stop()


# Thread spun off when the server is started to listen for incoming client connections, and send out any
# events that have been queued by the hooks in the debugger command class
class ServerThread (threading.Thread):
    def run(self):
        # Make sure there's no left over socket
        try:
            os.remove(_sock())
        except:
            pass

        # Create a server socket instance
        serv = ServerSocket(_sock())
        self.lock = threading.Lock()
        self.set_should_exit(False)

        # Main event loop
        while not self.should_exit():
            # Check sockets for activity
            asyncore.loop(count=1, timeout=0.1)

            # Process any events in the queue
            while not queue.empty():
                client, event = queue.get()
                client.send_event(event)

        # Clean up
        for client in clients:
            client.close()
        serv.close()
        try:
            os.remove(_sock())
        except:
            pass

    def should_exit(self):
        self.lock.acquire()
        r = self._should_exit
        self.lock.release()
        return r

    def set_should_exit(self, should_exit):
        self.lock.acquire()
        self._should_exit = should_exit
        self.lock.release()


# Socket for talking to an individual client
class ClientHandler (asyncore.dispatcher):
    def __init__(self, sock):
        asyncore.dispatcher.__init__(self, sock)
        self.registration = None

    def handle_read(self):
        data = self.recv(READ_MAX)
        if data.strip() != "":
            try:
                msg = pickle.loads(data)
                log.debug('Received msg: ' + str(msg))
            except Exception as e:
                log.error('Exception: ' + str(e))
                log.error('Invalid message data: ' + data)

            if msg['msg_type'] == 'register':
                self.handle_register(msg)
            elif msg['msg_type'] == 'push_update':
                self.handle_push_update(msg)
            else:
                log.error('Invalid message type: ' + msg['msg_type'])

    def handle_register(self, msg):
        log.debug('Registering client {} with config: {}'.format(self, str(msg['config'])))
        self.registration = msg

    def handle_push_update(self, msg):
        log.debug('Got a push update from client {} of type {} with data: {}'.format(self, msg['update_type'], str(msg['data'])))
        event = {'msg_type': 'update', 'data': msg['data']}
        for client in clients:
            if client.registration != None and client.registration['config']['type'] == msg['update_type']:
                queue.put((client, event))
        self.send(pickle.dumps({'msg_type': 'ack'}))

    def handle_close(self):
        self.close()
        if self in clients:
            clients.remove(self)

    def send_event(self, event):
        log.debug('Sending event to client {}: {}'.format(self, event))
        self.send(pickle.dumps(event))

    def writable(self):
        return False


# Main server socket for accept()s
class ServerSocket (asyncore.dispatcher):
    def __init__(self, sockfile):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.bind(sockfile)
        self.listen(1)

    def handle_accept(self):
        global clients
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            try:
                client = ClientHandler(sock)
                clients.append(client)
            except Exception as e:
                log.error("Exception handling accept: " + str(e))

    def writable(self):
        return False

