from __future__ import print_function

import os
import sys
import logging
import pprint
import re
import signal
import time
import argparse
from blessings import Terminal

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
    have_pygments = True
except:
    have_pygments = False

from collections import defaultdict

from scruffy import Config

from .core import *
from .colour import *
from .plugin import *

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
        if 'aliases' in kwargs:
            aliases = kwargs['aliases']
            del kwargs['aliases']
        else:
            aliases = []

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
                    chars.append('\033'+chunk)
                else:
                    p = chunk.find('m')
                    if p > 0:
                        chars.append('\033'+chunk[:p+1])
                        chars.extend(list(chunk[p+1:]))
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


class VoltronView (object):
    """
    Parent class for all views.
    """
    view_type = None

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
            sp = subparsers.add_parser(cls.view_type, aliases=cls._plugin.aliases)
        else:
            sp = subparsers.add_parser(cls.view_type)
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=cls)

    def __init__(self, args={}, loaded_config={}):
        log.debug('Loading view: ' + self.__class__.__name__)
        self.client = Client()
        self.pm = None
        self.args = args
        self.loaded_config = loaded_config

        # Commonly set by render method for header and footer formatting
        self.title = ''
        self.info = ''

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

        # Initialise window
        self.init_window()

        # Setup a SIGWINCH handler so we do reasonable things on resize
        signal.signal(signal.SIGWINCH, self.sigwinch_handler)

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

    def run(self):
        res = None
        os.system('clear')
        while True:
            try:
                # Connect to server
                if not self.client.is_connected:
                    self.client.connect()

                # If this is the first iteration (ie. we were just launched and the debugger is already stopped),
                # or we got a valid response on the last iteration, render
                if res == None or hasattr(res, 'state') and res.state == 'stopped':
                    self.render()

                # wait for the debugger to stop again
                wait_req = api_request('wait')
                res = self.client.send_request(wait_req)
            except socket.error, e:
                import traceback;traceback.print_exc()
                # if we're not connected, render an error and try again in a second
                self.do_render(error='Error: {}'.format(e.strerror))
                time.sleep(1)
            except SocketDisconnected as e:
                pass

    def render(self):
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
    def init_window(self):
        # Hide cursor
        os.system('tput civis')

    def cleanup(self):
        log.debug('Cleaning up view')
        os.system('tput cnorm')

    def clear(self):
        os.system('clear')

    def render(self):
        self.do_render()

    def do_render(self, error=None):
        # Clear the screen
        self.clear()

        # If we got an error, we'll use that as the body
        if error:
            self.body = self.colour(error, 'red')

        # Refresh the formatted body
        self.fmt_body = self.body

        # Pad and truncate the body
        self.pad_body()
        self.truncate_body()

        # Print the header, body and footer
        try:
            if self.config.header.show:
                print(self.format_header_footer(self.config.header))
            print(self.fmt_body, end='')
            if self.config.footer.show:
                print('\n' + self.format_header_footer(self.config.footer), end='')
            sys.stdout.flush()
        except IOError, e:
            # if we get an EINTR while printing, just do it again
            if e.errno == socket.EINTR:
                self.do_render()

    def sigwinch_handler(self, sig, stack):
        self.do_render()

    def window_size(self):
        height, width = os.popen('stty size').read().split()
        height = int(height)
        width = int(width)
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
        if colour != None:
            s += fmt_esc(colour)
        if background != None:
            s += fmt_esc('b_'+background)
        if attrs != []:
            s += ''.join(map(lambda x: fmt_esc('a_'+x), attrs))
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
        data = l + (width - llen - rlen)*p + r

        return data

    def pad_body(self):
        height, width = self.window_size()
        lines = self.fmt_body.split('\n')
        pad = self.body_height() - len(lines)
        if pad < 0:
            pad = 0
        self.fmt_body += int(pad)*'\n'

    def truncate_body(self):
        height, width = self.window_size()

        # truncate lines horizontally
        lines = []
        for line in self.fmt_body.split('\n'):
            s = AnsiString(line)
            if len(s) > width:
                line = s[:width-1] + self.colour('>', 'red')
            lines.append(line)

        # truncate body vertically
        lines = lines[:self.body_height()]

        self.fmt_body = '\n'.join(lines)


def merge(d1, d2):
    for k1,v1 in d1.items():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2