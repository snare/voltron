from __future__ import print_function

import os
import sys
import logging
import pprint
import re
import signal
import argparse
import subprocess
import socket
from blessed import Terminal

try:
    import urwid
except:
    urwid = None

try:
    import cursor
except:
    cursor = None

import voltron
from .core import Client
from .colour import fmt_esc
from .plugin import *
from .api import BlockingNotSupportedError

log = logging.getLogger("view")

ADDR_FORMAT_128 = '0x{0:0=32X}'
ADDR_FORMAT_64 = '0x{0:0=16X}'
ADDR_FORMAT_32 = '0x{0:0=8X}'
ADDR_FORMAT_16 = '0x{0:0=4X}'
SHORT_ADDR_FORMAT_128 = '{0:0=32X}'
SHORT_ADDR_FORMAT_64 = '{0:0=16X}'
SHORT_ADDR_FORMAT_32 = '{0:0=8X}'
SHORT_ADDR_FORMAT_16 = '{0:0=4X}'


# https://gist.github.com/sampsyo/471779
class AliasedSubParsersAction(argparse._SubParsersAction):
    class _AliasedPseudoAction(argparse.Action):
        def __init__(self, name, aliases, help):
            dest = name
            if aliases:
                dest += ' (%s)' % ','.join(aliases)
            sup = super(AliasedSubParsersAction._AliasedPseudoAction, self)
            sup.__init__(option_strings=[], dest=dest, help=help)

    def add_parser(self, name, **kwargs):
        aliases = kwargs.pop('aliases', [])
        parser = super(AliasedSubParsersAction, self).add_parser(name, **kwargs)

        # Make the aliases work.
        for alias in aliases:
            self._name_parser_map[alias] = parser
        # Make the help text reflect them, first removing old help entry.
        if 'help' in kwargs:
            help = kwargs.pop('help')
            self._choices_actions.pop()
            pseudo_action = self._AliasedPseudoAction(name, aliases, help)
            self._choices_actions.append(pseudo_action)

        return parser


class AnsiString(object):
    def __init__(self, string):
        chunks = string.split('\033')
        self.chars = []
        chars = list(chunks[0])

        if len(chunks) > 1:
            for chunk in chunks[1:]:
                if chunk == '(B':
                    chars.append('\033' + chunk)
                else:
                    p = chunk.find('m')
                    if p > 0:
                        chars.append('\033' + chunk[:p + 1])
                        chars.extend(list(chunk[p + 1:]))
                    else:
                        chars.extend(list(chunk))

        # roll up ansi sequences
        ansi = []
        for char in chars:
            if char[0] == '\033':
                ansi.append(char)
            else:
                self.chars.append(''.join(ansi) + char)
                ansi = []
        if len(self.chars) > 2:
            if self.chars[-1][0] == '\033':
                self.chars[-2] = self.chars[-2] + self.chars[-1]
                self.chars = self.chars[:-1]

    def __getitem__(self, key):
        if isinstance(key, slice):
            return ''.join(self.chars[key.start:key.stop]) + '\033[0m'
        else:
            return self.chars[key]

    def __str__(self):
        return ''.join(self.chars)

    def __len__(self):
        return len(self.chars)

    def clean(self):
        return re.sub('\033\[.{1,2}m', '', str(self))


def requires_async(func):
    def inner(self, *args, **kwargs):
        if not self.block:
            return func(self, *args, **kwargs)
        else:
            sys.stdout.write('\a')
            sys.stdout.flush()
    return inner


class VoltronView (object):
    """
    Parent class for all views.

    Views may or may not support blocking mode. LLDB can be queried from a background thread, which means requests can
    (if it makes sense) be fulfilled as soon as they're received. GDB cannot be queried from a background thread, so
    requests have to be queued and dispatched by the main thread when the debugger stops. This means that GDB requires
    blocking mode.

    In blocking mode, the view's `render` method must make a single call to Client's send_request/send_request method,
    with the request(s) flagged as blocking (block=True). If a view (or, more likely, a more complex client) has
    multiple calls to send_request/send_requests, then it cannot support blocking mode and should be flagged as such
    by including `supports_blocking = False` (see below, views are flagged as supporting blocking by default).

    All of the included Voltron views support blocking mode, but this distinction has been made so that views can be
    written for LLDB only without making compromises to support GDB.
    """
    view_type = None
    block = False
    supports_blocking = True

    @classmethod
    def add_generic_arguments(cls, sp):
        sp.add_argument('--show-header', '-e', dest="header", action='store_true', help='show header', default=None)
        sp.add_argument('--hide-header', '-E', dest="header", action='store_false', help='hide header')
        sp.add_argument('--show-footer', '-f', dest="footer", action='store_true', help='show footer', default=None)
        sp.add_argument('--hide-footer', '-F', dest="footer", action='store_false', help='hide footer')
        sp.add_argument('--name', '-n', action='store', help='named configuration to use', default=None)

    @classmethod
    def configure_subparser(cls, subparsers):
        if hasattr(cls._plugin, 'aliases'):
            sp = subparsers.add_parser(cls.view_type, aliases=cls._plugin.aliases, help='{} view'.format(cls.view_type))
        else:
            sp = subparsers.add_parser(cls.view_type, help='{} view'.format(cls.view_type))
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=cls)

    def __init__(self, args={}, loaded_config={}):
        log.debug('Loading view: ' + self.__class__.__name__)
        self.client = Client(url=voltron.config.view.api_url)
        self.pm = None
        self.args = args
        self.loaded_config = loaded_config
        self.server_version = None

        # Commonly set by render method for header and footer formatting
        self.title = ''
        self.info = ''
        self.body = ''

        # Build configuration
        self.build_config()

        log.debug("View config: " + pprint.pformat(self.config))
        log.debug("Args: " + str(self.args))

        # Let subclass do any setup it needs to do
        self.setup()

        # Override settings from command line args
        if self.args.header != None:
            self.config.header.show = self.args.header
        if self.args.footer != None:
            self.config.footer.show = self.args.footer

        # Setup a SIGWINCH handler so we do reasonable things on resize
        try:
            signal.signal(signal.SIGWINCH, self.sigwinch_handler)
        except:
            pass

    def build_config(self):
        # Start with all_views config
        self.config = self.loaded_config.view.all_views

        # Add view-specific config
        self.config.type = self.view_type
        name = self.view_type + '_view'
        if 'view' in self.loaded_config and name in self.loaded_config.view:
            self.config.update(self.loaded_config.view[name])

        # Add named config
        if self.args.name != None:
            self.config.update(self.loaded_config[self.args.name])

        # Apply view-specific command-line args
        self.apply_cli_config()

    def apply_cli_config(self):
        if self.args.header != None:
            self.config.header.show = self.args.header
        if self.args.footer != None:
            self.config.footer.show = self.args.footer

    def setup(self):
        log.debug('Base view class setup')

    def cleanup(self):
        log.debug('Base view class cleanup')

    def render(self, results):
        log.warning('Might wanna implement render() in this view eh')

    def do_render(error=None):
        pass

    def should_reconnect(self):
        try:
            return self.loaded_config.view.reconnect
        except:
            return True

    def sigwinch_handler(self, sig, stack):
        pass


class TerminalView (VoltronView):
    valid_key_funcs = ["exit", "page_up", "page_down", "page_up", "page_down",
                       "line_up", "line_down", "reset"]

    def __init__(self, *a, **kw):
        self.init_window()
        self.trunc_top = False
        self.done = False
        self.last_body = None
        self.scroll_offset = 0
        super(TerminalView, self).__init__(*a, **kw)

    def init_window(self):
        self.t = Terminal()
        print(self.t.civis)
        if cursor:
            cursor.hide()

    def cleanup(self):
        log.debug('Cleaning up view')
        print(self.t.cnorm)
        if cursor:
            cursor.show()

    def clear(self):
        # blessed's clear doesn't work properly on windaz
        # maybe figure out the right way to do it some time
        os.system('clear')

    def render(self, results):
        self.do_render()

    def do_render(self, error=None):
        # If we got an error, we'll use that as the body
        if error:
            self.body = self.colour(error, 'red')

        # Refresh the formatted body
        self.fmt_body = self.body

        # Pad and truncate the body
        self.pad_body()
        self.truncate_body()

        if self.body != self.last_body:
            # Clear the screen
            self.clear()

            # Print the header, body and footer
            try:
                if self.config.header.show:
                    print(self.format_header_footer(self.config.header))
                print(self.fmt_body, end='')
                if self.config.footer.show:
                    print('\n' + self.format_header_footer(self.config.footer), end='')
                sys.stdout.flush()
            except IOError as e:
                # if we get an EINTR while printing, just do it again
                if e.errno == socket.EINTR:
                    self.do_render()

        self.last_body = self.body

    def sigwinch_handler(self, sig, stack):
        self.do_render()

    def window_size(self):
        height, width = subprocess.check_output(['stty', 'size']).split()
        height = int(height) - int(self.config.pad.pad_bottom)
        width = int(width) - int(self.config.pad.pad_right)
        return (height, width)

    def body_height(self):
        height, width = self.window_size()
        if self.config.header.show:
            height -= 1
        if self.config.footer.show:
            height -= 1
        return height

    def colour(self, text='', colour=None, background=None, attrs=[]):
        s = ''
        if colour:
            s += fmt_esc(colour)
        if background:
            s += fmt_esc('b_' + background)
        if attrs != []:
            s += ''.join(map(lambda x: fmt_esc('a_' + x), attrs))
        s += text
        s += fmt_esc('reset')
        return s

    def format_header_footer(self, c):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, c.label_left.name) if c.label_left.name != None else ''
        r = getattr(self, c.label_right.name) if c.label_right.name != None else ''
        p = c.pad
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = self.colour(l, c.label_left.colour, c.label_left.bg_colour, c.label_left.attrs)
        r = self.colour(r, c.label_right.colour, c.label_right.bg_colour, c.label_right.attrs)
        p = self.colour(p, c.colour, c.bg_colour, c.attrs)

        # Build
        data = l + (width - llen - rlen) * p + r

        return data

    def pad_body(self):
        height, width = self.window_size()
        lines = self.fmt_body.split('\n')
        pad = self.body_height() - len(lines)
        if pad < 0:
            pad = 0
        self.fmt_body += int(pad) * '\n'

    def truncate_body(self):
        height, width = self.window_size()

        # truncate lines horizontally
        lines = []
        for line in self.fmt_body.split('\n'):
            s = AnsiString(line)
            if len(s) > width:
                line = s[:width - 1] + self.colour('>', 'red')
            lines.append(line)

        # truncate body vertically
        if len(lines) > self.body_height():
            if self.trunc_top:
                lines = lines[len(lines) - self.body_height():]
            else:
                lines = lines[:self.body_height()]

        self.fmt_body = '\n'.join(lines)

    def build_requests(self):
        """
        Build requests for this view. Concrete view subclasses must implement
        this.
        """
        return []

    def run(self):
        """
        Run the view event loop.
        """
        def render(results=[], error=None):
            if len(results) and not results[0].timed_out:
                self.render(results)
            elif error:
                self.do_render(error=error)

        # start the client
        self.client.start(self.build_requests, render)

        # handle keyboard input
        try:
            with self.t.cbreak():
                val = ''
                while not self.done:
                    val = self.t.inkey(timeout=1)
                    if val:
                        self.handle_key(val)
        except KeyboardInterrupt:
            self.exit()

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
        except:
            raise

    def exit(self):
        self.cleanup()
        os._exit(0)

    @requires_async
    def page_up(self):
        self.scroll_offset += self.body_height()
        self.client.update()

    @requires_async
    def page_down(self):
        self.scroll_offset -= self.body_height()
        self.client.update()

    @requires_async
    def line_up(self):
        self.scroll_offset += 1
        self.client.update()

    @requires_async
    def line_down(self):
        self.scroll_offset -= 1
        self.client.update()

    @requires_async
    def reset(self):
        self.scroll_offset = 0
        self.client.update()
