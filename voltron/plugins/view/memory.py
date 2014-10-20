import logging

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger("view")

class MemoryView (TerminalView):
    view_type = 'memory'

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('memory', help='memory view')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.add_argument('--reverse', '-v', action='store_true', help='reverse the output', default=False)
        group = sp.add_mutually_exclusive_group(required=True)
        group.add_argument('--address', '-a', action='store', help='address (in hex) from which to start reading memory')
        group.add_argument('--command', '-c', action='store', help='command to execute resulting in the address from which to start reading memory. voltron will do his almighty best to find an address in the output by splitting it on whitespace and searching from the end of the list of tokens. e.g. "print \$rip + 0x1234"', default=None)
        group.add_argument('--register', '-r', action='store', help='register containing the address from which to start reading memory', default=None)
        sp.set_defaults(func=MemoryView)

    def render(self, error=None):
        height, width = self.window_size()

        # Set up header and error message if applicable
        self.title = "[memory]"
        if error != None:
            self.body = self.colour(error, 'red')
        else:
            addr = None
            if self.args.command:
                res = self.client.perform_request('command', command=self.args.command)
                if res.is_success:
                    for item in reversed(res.output.split()):
                        log.debug("checking item: {}".format(item))
                        try:
                            addr = int(item)
                            break
                        except:
                            try:
                                addr = int(item, 16)
                                break
                            except:
                                pass
            elif self.args.address:
                addr = int(self.args.address, 16)
            elif self.args.register:
                res = self.client.perform_request('registers')
                if res.is_success:
                    addr = res.registers[self.args.register]

            if addr != None:
                res = self.client.perform_request('memory', address=addr, length=self.body_height()*self.args.bytes)
                if res.is_success:
                    self.body = self.hexdump(res.memory, offset=addr, length=self.args.bytes,
                        addr_colour=self.config['format']['addr_colour']).strip()
                    if self.args.reverse:
                        self.body = '\n'.join(reversed(self.body.split('\n'))).strip()
                    self.info = '[0x{0:0=4x}:'.format(len(res.memory)) + ADDR_FORMAT_64.format(addr) + ']'
                else:
                    log.error("Error reading memory: {}".format(res.message))
                    self.body = self.colour(res.message, 'red')
                    self.info = '[0x{0:0=4x}:'.format(0) + self.config['format']['addr_format'].format(addr) + ']'
            else:
                self.body = ""
                self.info = "[no address]"

        self.pad_body()

        # Call parent's render method
        super(MemoryView, self).render()


class MemoryViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'memory'
    view_class = MemoryView
