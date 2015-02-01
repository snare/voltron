import logging
import struct

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger("view")

class MemoryView (TerminalView):
    printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('memory', help='memory view')
        VoltronView.add_generic_arguments(sp)
        group = sp.add_mutually_exclusive_group(required=False)
        group.add_argument('--deref', '-d', action='store_true', help=('display the data in a column one CPU word wide '
            'and dereference any valid pointers'), default=False)
        group.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.add_argument('--reverse', '-v', action='store_true', help='reverse the output', default=False)
        group = sp.add_mutually_exclusive_group(required=True)
        group.add_argument('--address', '-a', action='store', help='address (in hex) from which to start reading memory')
        group.add_argument('--command', '-c', action='store', help=('command to execute resulting in the address from '
            'which to start reading memory. voltron will do his almighty best to find an address in the output by '
            'splitting it on whitespace and searching from the end of the list of tokens. e.g. "print \$rip + 0x1234"'),
            default=None)
        group.add_argument('--register', '-r', action='store', help='register containing the address from which to start reading memory', default=None)
        sp.set_defaults(func=MemoryView)

    def render(self):
        height, width = self.window_size()

        # get info about target
        target = None
        res = self.client.perform_request('targets')
        if res and res.is_success and len(res.targets) > 0:
            target = res.targets[0]

        if target and self.args.deref:
            self.args.bytes = target['addr_size']

        if not self.title:
            self.title = "[memory]"

        # find the address we're reading memory from
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
            res = self.client.perform_request('registers', registers=[self.args.register])
            if res and res.is_success:
                addr = res.registers.values()[0]

        # read memory
        if addr != None:
            res = self.client.perform_request('memory', address=addr, length=self.body_height()*self.args.bytes)
            if res and res.is_success:

                lines = []
                for c in range(0, res.bytes, self.args.bytes):
                    chunk = res.memory[c:c+self.args.bytes]
                    addr_str = self.colour(self.format_address(addr + c, size=target['addr_size'], pad=False),
                                            self.config.format.addr_colour)
                    if self.args.deref:
                        fmt = ('<' if target['byte_order'] == 'little' else '>') + \
                                {2: 'H', 4: 'L', 8: 'Q'}[target['addr_size']]
                        pointer = list(struct.unpack(fmt, chunk))[0]
                        memory_str = ' '.join(["%02X" % ord(x) for x in chunk])
                        deref_res = self.client.perform_request('dereference', pointer=pointer)
                        if deref_res.is_success:
                            info_str = self.format_deref(deref_res.output)
                        else:
                            info_str = ''
                    else:
                        memory_str = ' '.join(["%02X" % ord(x) for x in chunk])
                        info_str = ''
                    ascii_str = ''.join(["%s" % ((ord(x) <= 127 and self.printable_filter[ord(x)]) or '.') for x in chunk])
                    divider = self.colour('|', self.config.format.divider_colour)
                    lines.append('{}: {} {} {} {} {}'.format(addr_str, memory_str, divider, ascii_str, divider, info_str))

                self.body = '\n'.join(reversed(lines)).strip() if self.args.reverse else '\n'.join(lines)
                self.info = '[0x{0:0=4x}:'.format(len(res.memory)) + self.config.format.addr_format.format(addr) + ']'
            else:
                log.error("Error reading memory: {}".format(res.message))
                self.body = self.colour(res.message, 'red')
                self.info = '[0x{0:0=4x}:'.format(0) + self.config.format.addr_format.format(addr) + ']'
        else:
            self.body = ""
            self.info = "[no address]"

        super(MemoryView, self).render()

    def format_address(self, address, size=8, pad=True, prefix='0x'):
        fmt = '{:' + ('0=' + str(size*2) if pad else '') + 'X}'
        addr_str = fmt.format(address)
        if prefix:
            addr_str = prefix + addr_str
        return addr_str

    def format_deref(self, deref, size=8):
        fmtd = []
        for t,item in deref:
            if t == "pointer":
                fmtd.append(self.format_address(item, size=size, pad=False))
            elif t == "string":
                item = item.replace('\n', '\\n')
                fmtd.append(self.colour('"' + item + '"', self.config.format.string_colour))
            elif t == "symbol":
                fmtd.append(self.colour('`' + item + '`', self.config.format.symbol_colour))
            elif t == "circular":
                fmtd.append(self.colour('(circular)', self.config.format.divider_colour))
        return self.colour(' => ', self.config.format.divider_colour).join(fmtd)


class MemoryViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'memory'
    view_class = MemoryView


class StackView(MemoryView):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('stack', help='stack view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=StackView)

    def render(self):
        self.args.reverse = True
        self.args.deref = True
        self.args.register = 'sp'
        self.args.command = None
        self.args.address = None
        self.args.bytes = None

        self.title = '[stack]'

        super(StackView, self).render()


class StackViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'stack'
    view_class = StackView
