import logging
import six
import binascii
import math
import struct
import pygments
import pygments.formatters
from pygments.token import *

from voltron.view import TerminalView, VoltronView
from voltron.plugin import ViewPlugin, api_request

log = logging.getLogger("view")


def requires_async(func):
    def inner(self, *args, **kwargs):
        if not self.block:
            return func(self, *args, **kwargs)
        else:
            sys.stdout.write('\a')
            sys.stdout.flush()

    return inner

class MemoryStrideView(TerminalView):
    #valid_key_funcs = ["dec_mode", "hex_mode", "exit", "page_up", "page_down", "page_up", "page_down",
    #                   "line_up", "line_down", "reset"]
    TerminalView.valid_key_funcs += ["toggle_signed", "toggle_length", "dec_mode", "hex_mode", "inc_row_len", "dec_row_len"]    #s:


    printable_filter = ''.join([(len(repr(chr(x))) == 3) and chr(x) or '.' for x in range(256)])


    async = True
    last_memory = None
    last_address = 0
    last_length = 0
    view_style = {'hex_or_dec':'hex', 'word_size':4, 'unsigned':True}

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('memorystride', help='display a chunk of memory', aliases=('ms', 'mems','memstride'))
        VoltronView.add_generic_arguments(sp)
        group = sp.add_mutually_exclusive_group(required=False)
        group.add_argument('--deref', '-d', action='store_true',
                           help='display the data in a column one CPU word wide and dereference any valid pointers',
                           default=False)
        group.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        group.add_argument('--words', '-w', action='store', type=int, help='machine words per line', default=0)
        group.add_argument('--stride', '-s', action='store', type=int, help='bytes between lines (default 128)', default=128)
        group.add_argument('--rows', '-o', action='store', type=int, help='Lines to print (default 32)', default=32)
        group.add_argument('--max', action='store', type=int, help='Lines to print (default 0)', default=0)
        sp.add_argument('--reverse', '-v', action='store_true', help='reverse the output', default=False)
        sp.add_argument('--track', '-t', action='store_true', help='track and highlight changes', default=True)
        sp.add_argument('--no-track', '-T', action='store_false', help='don\'t track and highlight changes')
        
        group = sp.add_mutually_exclusive_group(required=False)
        group.add_argument('--address', '-a', action='store',
                           help='address (in hex or decimal) from which to start reading memory')
        group.add_argument('--command', '-c', action='store',
                           help='command to execute resulting in the address from which to start reading memory. '
                                'voltron will do his almighty best to find an address. e.g. "print \$rip + 0x1234"',
                           default=None)
        group.add_argument('--register', '-r', action='store',
                           help='register containing the address from which to start reading memory', default=None)
        sp.set_defaults(func=MemoryStrideView)


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

        args['words'] = self.args.stride*self.args.rows
        args['offset'] = self.scroll_offset*self.args.stride if self.args.reverse else -self.scroll_offset*self.args.stride
        if self.args.max:
            args['length'] = self.args.max

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
            bytes_per_chunk = self.args.stride
            row_len = self.args.words*self.view_style['word_size'] if self.args.words else self.args.bytes
            m_res.memory = binascii.unhexlify(m_res.memory)
            read_bytes = min(self.args.max, m_res.bytes)
            for c in range(0, read_bytes, bytes_per_chunk):
                chunk = m_res.memory[c:c + row_len]
                yield (Name.Label, self.format_address(m_res.address + c, size=target['addr_size'], pad=False))
                yield (Name.Label, ': ')

                # Hex bytes
                byte_array = []
                #raw_byte_array = []
                for i, x in enumerate(six.iterbytes(chunk)):
                    n = "%02X" % x
                    token = Text if x else Comment #Set color white or teal
                    if self.last_memory:
                        byte_addr = m_res.address + c + i
                        last_end_addr = self.last_address + self.last_length
                        if self.args.track and byte_addr > self.last_address and byte_addr < last_end_addr:
                            if x != six.indexbytes(self.last_memory, byte_addr - self.last_address):
                                token = Error #Set color to red
                    byte_array.append((token, n))
                    #raw_byte_array.append(x)


                byte_array_words = [byte_array[i:i+ self.view_style['word_size']] for i in range(0, row_len, self.view_style['word_size'])]
                for i, word in enumerate(byte_array_words):
                    format_str = '>' #default Big Endian

                    if target['byte_order'] == 'little':
                        word.reverse()
                        format_str = '<'  # set to Little Endian

                    if self.view_style['hex_or_dec'] == 'hex':
                        for x in word:
                            yield x
                    else:
                        raw_offset = i*self.view_style['word_size'];
                        raw_word = chunk[raw_offset:raw_offset +  self.view_style['word_size']]
                        token = Text
                        for x in word:
                            if x[0] == Error:
                                token = Error
                        word_idx = int(math.log(self.view_style['word_size'],2))
                        word_size_mapping = ['b', 'h', 'i', 'q']
                        format_print_str_map = ['{:>-4d}','{:>-6d}','{:>-11d}','{:>-21d}']
                        format_size = word_size_mapping[word_idx]
                        if self.view_style['unsigned']:
                            format_size = format_size.upper()
                        format_str += format_size
                        word_val = struct.unpack(format_str, bytes(raw_word))
                        yield (token, format_print_str_map[word_idx].format(word_val[0]))
                    yield (Text, ' ')


                # ASCII representation
                yield (Punctuation, '| ')
                for i, x in enumerate(six.iterbytes(chunk)):
                    token = String.Char if x else Comment
                    if self.last_memory:
                        byte_addr = m_res.address + c + i
                        last_end_addr = self.last_address + self.last_length
                        if self.args.track and byte_addr > self.last_address and byte_addr < last_end_addr:
                            if x != six.indexbytes(self.last_memory, byte_addr - self.last_address ):
                                token = Error
                    yield (token, ((x <= 127 and self.printable_filter[x]) or '.'))
                yield (Punctuation, ' | ')


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
                self.last_length = m_res.bytes
        else:
            self.body = self.colour("Failed to get targets", 'red')

        if not self.title:
            self.title = "[memory]"

        super(MemoryStrideView, self).render(results)

    def format_address(self, address, size=8, pad=True, prefix='0x'):
        fmt = '{:' + ('0=' + str(size * 2) if pad else '') + 'X}'
        addr_str = fmt.format(address)
        if prefix:
            addr_str = prefix + addr_str
        return addr_str

    def handle_key(self, key):
        """
        Handle a keypress. Concrete subclasses can implement this method if
        custom keypresses need to be handled other than for exit and scrolling.
        """
        try:
            func = None
            if key.is_sequence:
                try:
                    func = self.config.keymap[key.name]
                except:
                    try:
                        func = self.config.keymap[key.code]
                    except:
                        func = self.config.keymap[str(key)]
            else:
                func = self.config.keymap[str(key)]

            if func in self.valid_key_funcs:
                getattr(self, func)()
            # else:
            #     print "Unmapped Key\n"
        except:
            raise

    #@requires_async
    def toggle_signed(self):
        self.view_style['unsigned'] = not self.view_style['unsigned']
        self.client.update()

    #@requires_async
    def toggle_length(self):
        x = int(math.log(self.view_style['word_size'], 2))
        x = (x+1)%4
        x=2**x
        self.view_style['word_size'] = x
        if self.args.bytes % self.view_style['word_size'] != 0:
            # force bytes to be an even multiple of the word_size
            self.args.bytes &= ~(self.view_style['word_size'] - 1)
        self.client.update()

    @requires_async
    def dec_mode(self):
        self.view_style['hex_or_dec'] = 'dec'
        self.client.update()

    @requires_async
    def hex_mode(self):
        self.view_style['hex_or_dec'] = 'hex'
        self.client.update()

    @requires_async
    def inc_row_len(self):
        if self.args.words:
            self.args.words += 1
        else:
            self.args.bytes += self.view_style['word_size']
            #force bytes to be an even multiple of the word_size
            self.args.bytes &= ~(self.view_style['word_size']-1)
        self.client.update()

    @requires_async
    def dec_row_len(self):
        if self.args.words:
            self.args.words -= 1
        else:
            self.args.bytes -= self.view_style['word_size']
            #force bytes to be an even multiple of the word_size
            self.args.bytes &= ~(self.view_style['word_size']-1)
        self.client.update()


class MemoryStrideViewPlugin(ViewPlugin):
    plugin_type = 'view'
    name = 'memorystride'
    view_class = MemoryStrideView



