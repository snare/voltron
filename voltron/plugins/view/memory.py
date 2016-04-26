import logging
import struct
import six

from voltron.view import *
from voltron.plugin import *
from voltron.api import *

log = logging.getLogger("view")


class MemoryView (TerminalView):
    printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])

    async = True

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('memory', help='display a chunk of memory', aliases=('m', 'mem'))
        VoltronView.add_generic_arguments(sp)
        group = sp.add_mutually_exclusive_group(required=False)
        group.add_argument('--deref', '-d', action='store_true',
                           help='display the data in a column one CPU word wide and dereference any valid pointers',
                           default=False)
        group.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.add_argument('--reverse', '-v', action='store_true', help='reverse the output', default=False)
        group = sp.add_mutually_exclusive_group(required=True)
        group.add_argument('--address', '-a', action='store',
                           help='address (in hex or decimal) from which to start reading memory')
        group.add_argument('--command', '-c', action='store',
                           help=('command to execute resulting in the address from which to start reading memory. '
                                 'voltron will do his almighty best to find an address. e.g. "print \$rip + 0x1234"'),
                           default=None)
        group.add_argument('--register', '-r', action='store',
                           help='register containing the address from which to start reading memory', default=None)
        sp.set_defaults(func=MemoryView)

    def render(self):
        height, width = self.window_size()
        target = None
        self.trunc_top = self.args.reverse

        # check args
        if self.args.register:
            args = {'register': self.args.register}
        elif self.args.command:
            args = {'command': self.args.command}
        else:
            if self.args.address.startswith('0x'):
                addr = int(self.args.address, 16)
            else:
                try:
                    addr = int(self.args.address, 10)
                except:
                    addr = int(self.args.address, 16)
            args = {'address': addr}
        if self.args.deref:
            args['words'] = height
        else:
            args['length'] = height * self.args.bytes

        # get memory and target info
        m_res, t_res = self.client.send_requests(
            api_request('memory', block=self.block, deref=self.args.deref is True, **args),
            api_request('targets', block=self.block))

        # don't render if it timed out, probably haven't stepped the debugger again
        if t_res.timed_out:
            return

        if t_res and t_res.is_success and len(t_res.targets) > 0:
            target = t_res.targets[0]

            if self.args.deref:
                self.args.bytes = target['addr_size']

            if m_res and m_res.is_success:
                lines = []
                for c in range(0, m_res.bytes, self.args.bytes):
                    chunk = m_res.memory[c:c + self.args.bytes]
                    addr_str = self.colour(self.format_address(m_res.address + c, size=target['addr_size'], pad=False),
                                           self.config.format.addr_colour)
                    if self.args.deref:
                        l = {2: 'H', 4: 'L', 8: 'Q'}[target['addr_size']]
                        fmt = '{}{}'.format(('<' if target['byte_order'] == 'little' else '>'), l)
                        info_str = ''
                        if len(chunk) == target['addr_size']:
                            pointer = list(struct.unpack(fmt, chunk))[0]
                            memory_str = ' '.join(["%02X" % x for x in six.iterbytes(chunk)])
                            info_str = self.format_deref(m_res.deref.pop(0))
                    else:
                        memory_str = ' '.join(["%02X" % x for x in six.iterbytes(chunk)])
                        info_str = ''
                    ascii_str = ''.join(["%s" % ((x <= 127 and self.printable_filter[x]) or '.') for x in six.iterbytes(chunk)])
                    divider = self.colour('|', self.config.format.divider_colour)
                    lines.append('{}: {} {} {} {} {}'.format(addr_str, memory_str, divider, ascii_str, divider, info_str))

                self.body = '\n'.join(reversed(lines)).strip() if self.args.reverse else '\n'.join(lines)
                self.info = '[0x{0:0=4x}:'.format(len(m_res.memory)) + self.config.format.addr_format.format(m_res.address) + ']'
            else:
                log.error("Error reading memory: {}".format(m_res.message))
                self.body = self.colour(m_res.message, 'red')
                self.info = ''
        else:
            self.body = self.colour("Failed to get targets", 'red')

        if not self.title:
            self.title = "[memory]"

        super(MemoryView, self).render()

    def format_address(self, address, size=8, pad=True, prefix='0x'):
        fmt = '{:' + ('0=' + str(size * 2) if pad else '') + 'X}'
        addr_str = fmt.format(address)
        if prefix:
            addr_str = prefix + addr_str
        return addr_str

    def format_deref(self, deref, size=8):
        fmtd = []
        for t, item in deref:
            if t == "pointer":
                fmtd.append(self.format_address(item, size=size, pad=False))
            elif t == "string":
                item = item.replace('\n', '\\n')
                fmtd.append(self.colour('"' + item + '"', self.config.format.string_colour))
            elif t == "unicode":
                item = item.replace('\n', '\\n')
                fmtd.append(self.colour('u"' + item + '"', self.config.format.string_colour))
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
        sp = subparsers.add_parser('stack', help='display a chunk of stack memory', aliases=('s', 'st'))
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
