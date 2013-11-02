import pdb
import socket
import sys

# Trying to debug a quirk in some code that gets called async by {ll,g}db?
#
# from .rdb import Rdb
# Rdb().set_trace()
#
# Then: telnet localhost 4444


socks = {}
# Only bind the socket once
def _sock(port):
    if port in socks:
        return socks[port]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    socks[port] = s
    return s

class Rdb(pdb.Pdb):
    def __init__(self, port=4444):
        self.old_stdout = sys.stdout
        self.old_stdin = sys.stdin
        self.skt = _sock(port)
        self.skt.listen(1)
        (clientsocket, address) = self.skt.accept()
        handle = clientsocket.makefile('rw')
        pdb.Pdb.__init__(self, completekey='tab', stdin=handle, stdout=handle)
        sys.stdout = sys.stdin = handle
