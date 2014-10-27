from __future__ import print_function

import os
import sys
import logging
import pprint
import re
import signal
import time
from blessings import Terminal

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
    have_pygments = True
except:
    have_pygments = False

from collections import defaultdict

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


class AnsiString(object):
    def __init__(self, string):
        chunks = string.split('\033')
        self.chars = []
        chars = list(chunks[0])

        if len(chunks) > 1:
            for chunk in chunks[1:]:
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
    @classmethod
    def add_generic_arguments(cls, sp):
        sp.add_argument('--show-header', '-e', dest="header", action='store_true', help='show header', default=None)
        sp.add_argument('--hide-header', '-E', dest="header", action='store_false', help='hide header')
        sp.add_argument('--show-footer', '-f', dest="footer", action='store_true', help='show footer', default=None)
        sp.add_argument('--hide-footer', '-F', dest="footer", action='store_false', help='hide footer')
        sp.add_argument('--name', '-n', action='store', help='named configuration to use', default=None)

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
            self.config['header']['show'] = self.args.header
        if self.args.footer != None:
            self.config['footer']['show'] = self.args.footer

        # Initialise window
        self.init_window()

        # Setup a SIGWINCH handler so we do reasonable things on resize
        # signal.signal(signal.SIGWINCH, lambda sig, stack: self.render())

    def build_config(self):
        # Start with all_views config
        self.config = self.loaded_config['view']['all_views']

        # Add view-specific config
        self.config['type'] = self.view_type
        name = self.view_type + '_view'
        if 'view' in self.loaded_config and name in self.loaded_config['view']:
            merge(self.loaded_config['view'][name], self.config)

        # Add named config
        if self.args.name != None:
            merge(self.loaded_config[self.args.name], self.config)

        # Apply view-specific command-line args
        self.apply_cli_config()

    def apply_cli_config(self):
        if self.args.header != None:
            self.config['header']['show'] = self.args.header
        if self.args.footer != None:
            self.config['footer']['show'] = self.args.footer

    def setup(self):
        log.debug('Base view class setup')

    def run(self):
        res = None
        os.system('clear')
        try:
            while True:
                # Connect to server
                try:
                    self.client.connect()
                    self.connected = True
                except socket.error, e:
                    self.connected = False

                if self.connected:
                    # if this is the first iteration, or we got a valid response on the last iteration, render
                    if res == None or hasattr(res, 'state') and res.state == 'stopped':
                        self.render()

                    # wait for the debugger to stop again
                    wait_req = api_request('wait')
                    res = self.client.send_request(wait_req)
                else:
                    # if we're not connected, try again in a second
                    time.sleep(1)
        except SocketDisconnected as e:
            if self.should_reconnect():
                log.debug("Restarting process: " + str(type(e)))
                self.reexec()
            else:
                raise

    def render(self, error=None):
        log.warning('Might wanna implement render() in this view eh')

    def should_reconnect(self):
        try:
            return self.loaded_config['view']['reconnect']
        except:
            return True

    def reexec(self):
        # Instead of trying to reset internal state, just exec ourselves again
        os.execv(sys.argv[0], sys.argv)


class TerminalView (VoltronView):
    def init_window(self):
        # Hide cursor
        os.system('tput civis')

    def cleanup(self):
        log.debug('Cleaning up view')
        os.system('tput cnorm')

    def clear(self):
        os.system('clear')

    def render(self, msg=None):
        self.clear()
        if self.config['header']['show']:
            print(self.format_header())
        print(self.body, end='')
        if self.config['footer']['show']:
            print('\n' + self.format_footer(), end='')
        sys.stdout.flush()

    def window_size(self):
        height, width = os.popen('stty size').read().split()
        height = int(height)
        width = int(width)
        return (height, width)

    def body_height(self):
        height, width = self.window_size()
        if self.config['header']['show']:
            height -= 1
        if self.config['footer']['show']:
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

    def format_header(self):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, self.config['header']['label_left']['name']) if self.config['header']['label_left']['name'] != None else ''
        r = getattr(self, self.config['header']['label_right']['name']) if self.config['header']['label_right']['name'] != None else ''
        p = self.config['header']['pad']
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = self.colour(l, self.config['header']['label_left']['colour'], self.config['header']['label_left']['bg_colour'], self.config['header']['label_left']['attrs'])
        r = self.colour(r, self.config['header']['label_right']['colour'], self.config['header']['label_right']['bg_colour'], self.config['header']['label_right']['attrs'])
        p = self.colour(p, self.config['header']['colour'], self.config['header']['bg_colour'], self.config['header']['attrs'])

        # Build header
        header = l + (width - llen - rlen)*p + r

        return header

    def format_footer(self):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, self.config['footer']['label_left']['name']) if self.config['footer']['label_left']['name'] != None else ''
        r = getattr(self, self.config['footer']['label_right']['name']) if self.config['footer']['label_right']['name'] != None else ''
        p = self.config['footer']['pad']
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = self.colour(l, self.config['footer']['label_left']['colour'], self.config['footer']['label_left']['bg_colour'], self.config['footer']['label_left']['attrs'])
        r = self.colour(r, self.config['footer']['label_right']['colour'], self.config['footer']['label_right']['bg_colour'], self.config['footer']['label_right']['attrs'])
        p = self.colour(p, self.config['footer']['colour'], self.config['footer']['bg_colour'], self.config['footer']['attrs'])

        # Build header and footer
        footer = l + (width - llen - rlen)*p + r

        return footer

    def pad_body(self):
        height, width = self.window_size()

        # Split body into lines
        lines = self.body.split('\n')

        # Subtract lines (including wrapped lines)
        pad = self.body_height()
        for line in lines:
            line = ''.join(re.split('\033\[\d+m', line))
            (n, rem) = divmod(len(line), width)
            if rem > 0: n += 1
            pad -= n

        # If we have too much data for the view, too bad
        if pad < 0:
            pad = 0

        self.body += int(pad)*'\n'

    def truncate_body(self):
        height, width = self.window_size()

        lines = []
        for line in self.body.split('\n'):
            s = AnsiString(line)
            if len(s) > width:
                line = s[:width-1] + self.colour('>', 'red')
            lines.append(line)

        self.body = '\n'.join(lines)


def merge(d1, d2):
    for k1,v1 in d1.items():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2