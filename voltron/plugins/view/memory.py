import logging
import six
import pygments
import pygments.formatters
from pygments.token import *

from voltron.view import TerminalView, VoltronView
from voltron.plugin import ViewPlugin, api_request

log = logging.getLogger("view")


class MemoryView(TerminalView):
    printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])

    async = True
    last_memory = None
    last_address = 0

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
        sp.add_argument('--track', '-t', action='store_true', help='track and highlight changes', default=True)
        sp.add_argument('--no-track', '-T', action='store_false', help='don\'t track and highlight changes')
        sp.add_argument('--words', '-w', action='store_true', help='display data as a column of machine words', default=False)
        group = sp.add_mutually_exclusive_group(required=False)
        group.add_argument('--address', '-a', action='store',
                           help='address (in hex or decimal) from which to start reading memory')
        group.add_argument('--command', '-c', action='store',
                           help='command to execute resulting in the address from which to start reading memory. '
                                'voltron will do his almighty best to find an address. e.g. "print \$rip + 0x1234"',
                           default=None)
        group.add_argument('--register', '-r', action='store',
                           help='register containing the address from which to start reading memory', default=None)
        sp.set_defaults(func=MemoryView)

    def build_requests(self):
        height, width = self.window_size()

        # check args
        if self.args.register:
            args = {'register': self.args.register}
        elif self.args.command:
            args = {'command': self.args.command}
        elif self.args.address:
            if self.args.address.startswith('0x'):
                addr = int(self.args.address, 16)
            else:
                try:
                    addr = int(self.args.address, 10)
                except:
                    addr = int(self.args.address, 16)
            args = {'address': addr}
        else:
            args = {'register': 'sp'}

        if self.args.deref:
            args['words'] = height
            args['offset'] = self.scroll_offset if self.args.reverse else -self.scroll_offset
        else:
            args['length'] = height * self.args.bytes
            args['offset'] = self.scroll_offset * self.args.bytes * (1 if self.args.reverse else -1)

        # get memory and target info
        return [
            api_request('targets'),
            api_request('memory', deref=self.args.deref is True, **args)
        ]

    def generate_tokens(self, results):
        t_res, m_res = results

        if t_res and t_res.is_success and len(t_res.targets) > 0:
            target = t_res.targets[0]

        if m_res and m_res.is_success:
            for c in range(0, m_res.bytes, self.args.bytes):
                chunk = m_res.memory[c:c + self.args.bytes]
                yield (Name.Label, self.format_address(m_res.address + c, size=target['addr_size'], pad=False))
                yield (Name.Label, ': ')

                # Hex bytes
                byte_array = []
                for i, x in enumerate(six.iterbytes(chunk)):
                    n = "%02X" % x
                    if self.args.track and self.last_memory and self.last_address == m_res.address:
                        if x != six.indexbytes(self.last_memory, c + i):
                            byte_array.append((Error, n))
                        else:
                            byte_array.append((Text, n))
                    else:
                        byte_array.append((Text, n))

                if self.args.words:
                    if target['byte_order']  =='little':
                        byte_array.reverse()
                    for x in byte_array:
                        yield x
                    yield (Text, ' ')
                else:
                    for x in byte_array:
                        yield x
                        yield (Text, ' ')

                # ASCII representation
                yield (Punctuation, '| ')
                for i, x in enumerate(six.iterbytes(chunk)):
                    token = String.Char
                    if self.args.track and self.last_memory and self.last_address == m_res.address:
                        if x != six.indexbytes(self.last_memory, c + i):
                            token = Error
                    yield (token, ((x <= 127 and self.printable_filter[x]) or '.'))
                yield (Punctuation, ' | ')

                # Deref chain
                if self.args.deref:
                    chain = m_res.deref.pop(0)
                    for i, (t, item) in enumerate(chain):
                        if t == "pointer":
                            yield (Number.Hex, self.format_address(item, size=target['addr_size'], pad=False))
                        elif t == "string":
                            for r in ['\n', '\r', '\v']:
                                item = item.replace(r, '\\{:x}'.format(ord(r)))
                            yield (String.Double, '"' + item + '"')
                        elif t == "unicode":
                            for r in ['\n', '\r', '\v']:
                                item = item.replace(r, '\\{:x}'.format(ord(r)))
                            yield (String.Double, 'u"' + item + '"')
                        elif t == "symbol":
                            yield (Name.Function, '`' + item + '`')
                        elif t == "circular":
                            yield (Text, '(circular)')
                        if i < len(chain) - 1:
                            yield (Punctuation, ' => ')

                yield (Text, '\n')

    def render(self, results):
        target = None
        self.trunc_top = self.args.reverse

        t_res, m_res = results

        if t_res and t_res.is_success and len(t_res.targets) > 0:
            target = t_res.targets[0]

            if self.args.deref or self.args.words:
                self.args.bytes = target['addr_size']

            f = pygments.formatters.get_formatter_by_name(self.config.format.pygments_formatter,
                                                          style=self.config.format.pygments_style)

            if m_res and m_res.is_success:
                lines = pygments.format(self.generate_tokens(results), f).split('\n')
                self.body = '\n'.join(reversed(lines)).strip() if self.args.reverse else '\n'.join(lines)
                self.info = '[0x{0:0=4x}:'.format(len(m_res.memory)) + self.config.format.addr_format.format(m_res.address) + ']'
            else:
                log.error("Error reading memory: {}".format(m_res.message))
                self.body = pygments.format([(Error, m_res.message)], f)
                self.info = ''

            # Store the memory
            if self.args.track:
                self.last_address = m_res.address
                self.last_memory = m_res.memory
        else:
            self.body = self.colour("Failed to get targets", 'red')

        if not self.title:
            self.title = "[memory]"

        super(MemoryView, self).render(results)

    def format_address(self, address, size=8, pad=True, prefix='0x'):
        fmt = '{:' + ('0=' + str(size * 2) if pad else '') + 'X}'
        addr_str = fmt.format(address)
        if prefix:
            addr_str = prefix + addr_str
        return addr_str


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
        sp.add_argument('--track', '-t', action='store_true', help='track and highlight changes', default=True)
        sp.add_argument('--no-track', '-T', action='store_false', help='don\'t track and highlight changes')

    def build_requests(self):
        self.args.reverse = True
        self.args.deref = True
        self.args.words = False
        self.args.register = 'sp'
        self.args.command = None
        self.args.address = None
        self.args.bytes = None

        return super(StackView, self).build_requests()

    def render(self, results):
        self.title = '[stack]'

        super(StackView, self).render(results)


class StackViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'stack'
    view_class = StackView
