#!/usr/bin/env python

from __future__ import print_function

import os
import sys
import socket
import asyncore
import threading
import argparse
import logging
import logging.config
import Queue
import struct
import json
import curses

from collections import defaultdict
from termcolor import colored

try:
    import cPickle as pickle
except:
    import pickle

try:
    import gdb
    in_gdb = True
except:
    in_gdb = False

try:
    import lldb
    in_lldb = True
except:
    in_lldb = False

try:
    import pygments
    import pygments.lexers
    import pygments.formatters
    have_pygments = True
except:
    have_pygments = False

SOCK = "/tmp/voltron.sock"
READ_MAX = 0xFFFF
LOG_CONFIG = {
        'version': 1,
        'formatters': {
            'standard': {'format': 'voltron: [%(levelname)s] %(message)s'}
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard'
            }
        },
        'loggers': {
            '': {
                'handlers': ['default'],
                'level': 'INFO',
                'propogate': True,
            }
        }
}

ADDR_FORMAT_128 = '0x{0:0=32X}'
ADDR_FORMAT_64 = '0x{0:0=16X}'
ADDR_FORMAT_32 = '0x{0:0=8X}'
ADDR_FORMAT_16 = '0x{0:0=4X}'
SEGM_FORMAT_16 = '{0:0=4X}'

DISASM_MAX = 32
STACK_MAX = 64

log = None
clients = []
queue = None
inst = None
config = {}

def main(debugger=None, dict=None):
    global log, queue, inst, config

    # Configure logging
    logging.config.dictConfig(LOG_CONFIG)
    log = logging.getLogger('')

    # Load config
    try:
        config_data = file(os.path.expanduser('~/.voltron')).read()
        lines = filter(lambda x: len(x) != 0 and x[0] != '#', config_data.split('\n'))
        config = json.loads('\n'.join(lines))
    except:
        log.debug("No config file")

    # Set up queue
    queue = Queue.Queue()

    if in_gdb:
        # Load GDB command
        log.debug('Loading GDB command')
        print("Voltron loaded.")
        inst = VoltronGDBCommand()
    elif in_lldb:
        # Load LLDB command
        log.debug('Loading LLDB command')
        inst = VoltronLLDBCommand(debugger, dict)
    else:
        # Set up command line arg parser
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', '-d', action='store_true', help='print debug logging')
        subparsers = parser.add_subparsers(title='subcommands', description='valid subcommands', help='additional help')

        # Update the view base class
        base = CursesView if 'curses' in config.keys() and config['curses'] else TerminalView
        for cls in TerminalView.__subclasses__():
            cls.__bases__ = (base,)

        # Set up a subcommand for each view class 
        for cls in base.__subclasses__():
            cls.configure_subparser(subparsers)

        # And subcommands for the loathsome red-headed stepchildren
        StandaloneServer.configure_subparser(subparsers)
        GDB6Proxy.configure_subparser(subparsers)

        # Parse args
        args = parser.parse_args()
        if args.debug:
            log.setLevel(logging.DEBUG)

        # Instantiate and run the appropriate module
        inst = args.func(args)
        try:
            inst.run()
        except Exception as e:
            log.error("Exception running module {}: {}".format(inst.__class__.__name__, str(e)))
        except KeyboardInterrupt:
            pass
        inst.cleanup()
        log.info('Exiting')

def merge(d1, d2):
    for k1,v1 in d1.iteritems():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2


#
# Server side code
#

class VoltronCommand (object):
    running = False

    def handle_command(self, command):
        global log
        if "start" in command:
            if 'debug' in command:
                log.setLevel(logging.DEBUG)
            self.start()
        elif "stop" in command:
            self.stop()
        elif "status" in command:
            self.status()
        elif "update" in command:
            self.update()
        else:
            print("Usage: voltron <start|stop|update|status>")

    def start(self):
        if not self.running:
            print("Starting voltron")
            self.running = True
            self.register_hooks()
            self.thread = ServerThread()
            self.thread.start()
        else:
            print("Already running")

    def stop(self):
        if self.running:
            print("Stopping voltron")
            self.unregister_hooks()
            self.thread.set_should_exit(True)
            self.thread.join(10)
            if self.thread.isAlive():
                print("Failed to stop voltron :<")
            self.running = False
        else:
            print("Not running")

    def status(self):
        if self.running:
            print("There are {} clients attached".format(len(clients)))
            for client in clients:
                print("{} registered with config: {}".format(client, str(client.registration['config'])))
        else:
            print("Not running")

    def update(self):
        log.debug("Updating clients")

        for client in filter(lambda c: c.registration['config']['update_on'] == 'stop', clients):
            event = {'msg_type': 'update', }

            if client.registration['config']['type'] == 'cmd':
                event['data'] = self.get_cmd_output(client.registration['config']['cmd'])
            elif client.registration['config']['type'] == 'register':
                event['data'] = self.get_registers()
            elif client.registration['config']['type'] == 'disasm':
                event['data'] = self.get_disasm()
            elif client.registration['config']['type'] == 'stack':
                event['data'] = {'data': self.get_stack(), 'sp': self.get_register('rsp')}
            elif client.registration['config']['type'] == 'bt':
                event['data'] = self.get_backtrace()
                
            queue.put((client, event))

    def register_hooks(self):
        pass

    def unregister_hooks(self):
        pass


# This is the actual GDB command. Should be able to just add an LLDB version I guess.
if in_gdb:
    class VoltronGDBCommand (VoltronCommand, gdb.Command):
        def __init__(self):
            super(VoltronCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)
            self.running = False

        def invoke(self, arg, from_tty):
            self.handle_command(arg)

        def register_hooks(self):
            gdb.events.stop.connect(self.stop_handler)

        def unregister_hooks(self):
            gdb.events.stop.disconnect(self.stop_handler)

        def stop_handler(self, event):
            self.update()

        def get_registers(self):
            log.debug('Getting registers')
            regs = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15',
                    'cs','ds','es','fs','gs','ss','xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8',
                    'xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15']
            vals = {}
            for reg in regs:
                try:
                    vals[reg] = int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF
                except:
                    log.debug('Failed getting reg: ' + reg)
                    vals[reg] = 'N/A'
            try:
                vals['rflags'] = int(gdb.execute('info reg $eflags', to_string=True).split()[1], 16)
            except:
                log.debug('Failed getting reg: eflags')
                vals['rflags'] = 'N/A'
            log.debug('Got registers: ' + str(vals))
            return vals

        def get_register(self, reg):
            log.debug('Getting register: ' + reg)
            return int(gdb.parse_and_eval('(long long)$'+reg)) & 0xFFFFFFFFFFFFFFFF

        def get_disasm(self):
            log.debug('Getting disasm')
            res = gdb.execute('x/{}i $rip'.format(DISASM_MAX), to_string=True)
            return res

        def get_stack(self):
            log.debug('Getting stack')
            rsp = int(gdb.parse_and_eval('(long long)$rsp')) & 0xFFFFFFFFFFFFFFFF
            res = str(gdb.selected_inferior().read_memory(rsp, STACK_MAX*16))
            return res

        def get_backtrace(self):
            log.debug('Getting backtrace')
            res = gdb.execute('bt', to_string=True)
            return res

        def get_cmd_output(self, cmd=None):
            if cmd:
                log.debug('Getting command output: ' + cmd)
                res = gdb.execute(cmd, to_string=True)
            else:
                res = "<No command>"
            return res


if in_lldb:
    # LLDB's initialisation routine
    def __lldb_init_module(debugger, dict):
        main(debugger, dict)

    def lldb_invoke(debugger, command, result, dict):
        inst.invoke(debugger, command, result, dict)

    class VoltronLLDBCommand (VoltronCommand):
        debugger = None

        def __init__(self, debugger, dict):
            self.debugger = debugger
            debugger.HandleCommand('command script add -f voltron.lldb_invoke voltron')
            self.running = False

        def invoke(self, debugger, command, result, dict):
            self.debugger = debugger
            self.handle_command(command)

        def register_hooks(self):
            self.debugger.HandleCommand('target stop-hook add -o \'voltron update\'')

        def unregister_hooks(self):
            # XXX: Fix this so it only removes our stop-hook
            self.debugger.HandleCommand('target stop-hook delete')

        def get_frame(self):
            return self.debugger.GetTargetAtIndex(0).process.selected_thread.GetFrameAtIndex(0)

        def get_registers(self):
            log.debug('Getting registers')
            frame = self.get_frame()
            regs = {x.name:int(x.value, 16) for x in list(list(frame.GetRegisters())[0])}
            return regs

        def get_register(self, reg):
            log.debug('Getting register: ' + reg)
            return self.get_registers()[reg]

        def get_disasm(self):
            log.debug('Getting disasm')
            res = self.get_cmd_output('disassemble -c {}'.format(DISASM_MAX))
            return res

        def get_stack(self):
            log.debug('Getting stack')
            rsp = self.get_register('rsp')
            error = lldb.SBError()
            res = lldb.debugger.GetTargetAtIndex(0).process.ReadMemory(rsp, STACK_MAX*16, error)
            return res

        def get_backtrace(self):
            log.debug('Getting backtrace')
            res = self.get_cmd_output('bt')
            return res

        def get_cmd_output(self, cmd=None):
            if cmd:
                log.debug('Getting command output: ' + cmd)
                res = lldb.SBCommandReturnObject()
                self.debugger.GetCommandInterpreter().HandleCommand(cmd, res)
                res = res.GetOutput()
            else:
                res = "<No command>"
            return res


class StandaloneServer (object):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('server', help='standalone server for debuggers without python support')
        sp.set_defaults(func=StandaloneServer)

    def __init__(self, args={}):
        self.args = args

    def run(self):
        log.debug("Starting standalone server")
        self.thread = ServerThread()
        self.thread.start()
        while True: pass

    def cleanup(self):
        log.info("Exiting")
        self.thread.set_should_exit(True)
        self.thread.join(10)


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
            except:
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
        clients.remove(self)

    def send_event(self, event):
        log.debug('Sending event to client {}: {}'.format(self, event))
        self.send(pickle.dumps(event))


# Main server socket for accept()s
class Server (asyncore.dispatcher):
    def __init__(self, sockfile):
        asyncore.dispatcher.__init__(self)
        try:
            os.remove(SOCK)
        except:
            pass
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


# Thread spun off when the plugin is started to listen for incoming client connections, and send out any
# events that have been queued by the hooks in the debugger command class
class ServerThread (threading.Thread):
    def run(self):
        global clients, queue

        # Create a server instance
        serv = Server(SOCK)
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
        serv.close()

    def should_exit(self):
        self.lock.acquire()
        r = self._should_exit
        self.lock.release()
        return r

    def set_should_exit(self, should_exit):
        self.lock.acquire()
        self._should_exit = should_exit
        self.lock.release()


#
# Client-side code
#

# Socket to register with the server and receive messages, calls view's render() method when a message comes in
class Client (asyncore.dispatcher):
    def __init__(self, view=None, config={}):
        asyncore.dispatcher.__init__(self)
        self.view = view
        self.config = config
        self.reg_info = None
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connect(SOCK)

    def register(self):
        log.debug('Client {} registering with config: {}'.format(self, str(self.config)))
        msg = {'msg_type': 'register', 'config': self.config}
        log.debug('Sending: ' + str(msg))
        self.send(pickle.dumps(msg))

    def handle_read(self):
        data = self.recv(READ_MAX)
        try:
            msg = pickle.loads(data)
            log.debug('Received message: ' + str(msg))
        except Exception as e:
            log.error('Exception parsing message: ' + str(e))
            log.error('Invalid message: ' + data)

        try:
            if self.view:
                self.view.render(msg)
        except Exception as e:
            log.error('Error rendering view: ' + str(e))

    def writable(self):
        return False; 

# Parent class for all views
class VoltronView (object):
    DEFAULT_CONFIG = {
        "update_on": "stop",
        "clear": True,
        "header": {
            "show":         True,
            "pad":          " ",
            "colour":       "blue",
            "bg_colour":    "grey",
            "attrs":        [],
            "label_left": {
                "name":         "info",
                "colour":       "blue",
                "bg_colour":    "grey",
                "attrs":        []
            },
            "label_right": {
                "name":         "title",
                "colour":       "blue",
                "bg_colour":    "grey",
                "attrs":        ["bold"]
            }
        },
        "footer": {
            "show":         True,
            "pad":          " ",
            "colour":       "blue",
            "bg_colour":    "grey",
            "attrs":        [],
            "label_left": {
                "name":         None,
                "colour":       "blue",
                "bg_colour":    "grey",
                "attrs":        []
            },
            "label_right": {
                "name":         None,
                "colour":       "blue",
                "bg_colour":    "grey",
                "attrs":        ["bold"],
            }
        }
    }

    @classmethod
    def add_generic_arguments(cls, sp):
        sp.add_argument('--show-header', '-e', dest="header", action='store_true', help='show header', default=None)
        sp.add_argument('--hide-header', '-E', dest="header", action='store_false', help='hide header', default=None)
        sp.add_argument('--show-footer', '-f', dest="footer", action='store_true', help='show footer', default=None)
        sp.add_argument('--hide-footer', '-F', dest="footer", action='store_false', help='hide footer', default=None)

    def __init__(self, args={}):
        global config
        log.debug('Loading view: ' + self.__class__.__name__)
        self.client = None
        self.args = args

        # Common set by render method for header and footer formatting
        self.title = ''
        self.info = ''

        # Set config defaults
        self.config = self.DEFAULT_CONFIG
        try:
            merge(config['all_views'], self.config)
        except:
            pass

        # Let subclass set stuff up
        self.setup()

        # Load subclass view config
        try:
            merge(config[self.config['type']+'_view'], self.config)
        except:
            pass

        # Override settings from command line args
        if self.args.header != None:
            self.config['header']['show'] = self.args.header
        if self.args.footer != None:
            self.config['footer']['show'] = self.args.footer

        log.debug("View config: " + str(self.config))
        log.debug("Args: " + str(self.args))

        # Initialise window
        self.init_window()        

        # Connect to server
        self.connect()

    def setup(self):
        log.debug('Base view class setup')

    def connect(self):
        try:
            self.client = Client(view=self, config=self.config)
            self.client.register()
        except Exception as e:
            log.error('Exception connecting: ' + str(e))
            raise e

    def run(self):
        os.system('clear')
        log.info('Waiting for an update from the debugger')
        asyncore.loop()

    def render(self, msg=None):
        log.warning('Might wanna implement render() in this view eh')

    def hexdump(self, src, length=16, sep='.', offset=0):
        FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
        lines = []
        for c in xrange(0, len(src), length):
            chars = src[c:c+length]
            hex = ' '.join(["%02X" % ord(x) for x in chars])
            if len(hex) > 24:
                hex = "%s %s" % (hex[:24], hex[24:])
            printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
            lines.append("%s:  %-*s  |%s|\n" % (ADDR_FORMAT_64.format(offset+c), length*3, hex, printable))
        return ''.join(lines).strip()

    def format_header(self):
        height, width = self.window_size()

        # Get values for labels
        l = getattr(self, self.config['header']['label_left']['name']) if self.config['header']['label_left']['name'] != None else ''
        r = getattr(self, self.config['header']['label_right']['name']) if self.config['header']['label_right']['name'] != None else ''
        p = self.config['header']['pad']
        llen = len(l)
        rlen = len(r)

        # Add colour
        l = colored(l, self.config['header']['label_left']['colour'], 'on_' + self.config['header']['label_left']['bg_colour'], self.config['header']['label_left']['attrs'])
        r = colored(r, self.config['header']['label_right']['colour'], 'on_' + self.config['header']['label_right']['bg_colour'], self.config['header']['label_right']['attrs'])
        p = colored(p, self.config['header']['colour'], 'on_' + self.config['header']['bg_colour'], self.config['header']['attrs'])

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
        l = colored(l, self.config['footer']['label_left']['colour'], 'on_' + self.config['footer']['label_left']['bg_colour'], self.config['footer']['label_left']['attrs'])
        r = colored(r, self.config['footer']['label_right']['colour'], 'on_' + self.config['footer']['label_right']['bg_colour'], self.config['footer']['label_right']['attrs'])
        p = colored(p, self.config['footer']['colour'], 'on_' + self.config['footer']['bg_colour'], self.config['footer']['attrs'])

        # Build header and footer
        footer = l + (width - llen - rlen)*p + r
        
        return footer


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


class CursesView (VoltronView):
    def init_window(self):
        self.screen = curses.initscr()
        self.screen.border(0)

    def cleanup(self):
        curses.endwin()

    def render(self, msg=None):
        self.screen.clear()
        y = 0
        if self.config['header']['show']:
            self.screen.addstr(0, 0, self.header)
            y = 1
        self.screen.addstr(0, y, self.body)
        self.screen.refresh()

    def clear(self):
        # Clear the window - this sucks, should probably do it with ncurses at some stage
        os.system('clear')

    def window_size(self):
        # Get terminal size - this also sucks, but curses sucks more
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


# Class to actually render the view
class RegisterView (TerminalView):
    FORMAT_DEFAULTS = {
        'label_format':     '{0}:',
        'label_func':       str.upper,
        'label_colour':     'green',
        'label_colour_en':  True,
        'value_format':     ADDR_FORMAT_64,
        'value_func':       None,
        'value_colour':     'grey',
        'value_colour_mod': 'red',
        'value_colour_en':  True
    }
    FORMAT_INFO = {
        'x64': [
            {
                'regs':             ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip',
                                     'r8','r9','r10','r11','r12','r13','r14','r15'],
                'label_format':     '{0:3s}:',
            },
            {
                'regs':             ['cs','ds','es','fs','gs','ss'],
                'value_format':     SEGM_FORMAT_16,
            },
            {
                'regs':             ['xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7','xmm8',
                                     'xmm9','xmm10','xmm11','xmm12','xmm13','xmm14','xmm15'],
                'value_format':     ADDR_FORMAT_128,
            },
            {
                'regs':             ['rflags'],
                'value_format':     '{}',
                'value_func':       'self.format_flags',
                'value_colour_en':  False
            }
        ]
    }
    TEMPLATE_H = (
        "{raxl} {rax}  {rbxl} {rbx}  {rbpl} {rbp}  {rspl} {rsp}  {rflags}\n"
        "{rdil} {rdi}  {rsil} {rsi}  {rdxl} {rdx}  {rcxl} {rcx}  {ripl} {rip}\n"
        "{r8l} {r8}  {r9l} {r9}  {r10l} {r10}  {r11l} {r11}  {r12l} {r12}\n"
        "{r13l} {r13}  {r14l} {r14}  {r15l} {r15}\n"
        "{csl} {cs}  {dsl} {ds}  {esl} {es}  {fsl} {fs}  {gsl} {gs}  {ssl} {ss}"
    )
    TEMPLATE_V = (
        " {rflags}\n"
        "{ripl} {rip}\n"
        "{raxl} {rax}\n{rbxl} {rbx}\n{rbpl} {rbp}\n{rspl} {rsp}\n"
        "{rdil} {rdi}\n{rsil} {rsi}\n{rdxl} {rdx}\n{rcxl} {rcx}\n"
        "{r8l} {r8}\n{r9l} {r9}\n{r10l} {r10}\n{r11l} {r11}\n{r12l} {r12}\n"
        "{r13l} {r13}\n{r14l} {r14}\n{r15l} {r15}\n"
        "{csl}  {cs}  {dsl}  {ds}\n{esl}  {es}  {fsl}  {fs}\n{gsl}  {gs}  {ssl}  {ss}"
    )
    FLAG_BITS = {'c': 0, 'p': 2, 'a': 4, 'z': 6, 's': 7, 't': 8, 'i': 9, 'd': 10, 'o': 11}
    FLAG_TEMPLATE = "[ {o} {d} {i} {t} {s} {z} {a} {p} {c} ]"
    SSE_TEMPLATE_H = (
        "{xmm0l}  {xmm0} {xmm1l}  {xmm1} {xmm2l}  {xmm2}\n"
        "{xmm3l}  {xmm3} {xmm4l}  {xmm4} {xmm5l}  {xmm5}\n"
        "{xmm6l}  {xmm6} {xmm7l}  {xmm7} {xmm8l}  {xmm8}\n"
        "{xmm9l}  {xmm9} {xmm10l} {xmm10} {xmm11l} {xmm11}\n"
        "{xmm12l} {xmm12} {xmm13l} {xmm13} {xmm14l} {xmm14}\n"
        "{xmm15l} {xmm15}\n"
    )
    SSE_TEMPLATE_V = (
        "{xmm0l}  {xmm0}\n{xmm1l}  {xmm1}\n{xmm2l}  {xmm2}\n{xmm3l}  {xmm3}\n"
        "{xmm4l}  {xmm4}\n{xmm5l}  {xmm5}\n{xmm6l}  {xmm6}\n{xmm7l}  {xmm7}\n"
        "{xmm8l}  {xmm8}\n{xmm9l}  {xmm9}\n{xmm10l} {xmm10}\n{xmm11l} {xmm11}\n"
        "{xmm12l} {xmm12}\n{xmm13l} {xmm13}\n{xmm14l} {xmm14}\n{xmm15l} {xmm15}"
    )
    last_regs = None
    last_flags = None

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('reg', help='register view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=RegisterView)
        g = sp.add_mutually_exclusive_group()
        g.add_argument('--horizontal', '-o', action='store_true', help='horizontal orientation (default)', default=False)
        g.add_argument('--vertical', '-v', action='store_true', help='vertical orientation', default=True)
        sp.add_argument('--sse', '-s', action='store_true', help='show sse registers', default=False)

    def setup(self):
        global config
        self.config['type'] = 'register'
        try:
            self.format_defaults = dict(self.FORMAT_DEFAULTS.items() + self.config['format_defaults'].items())
        except:
            self.format_defaults = self.FORMAT_DEFAULTS

    def render(self, msg=None):
        # Grab the appropriate template
        if self.args.horizontal:
            template = self.TEMPLATE_H
            if self.args.sse:
                template += '\n' + self.SSE_TEMPLATE_H
        else:
            template = self.TEMPLATE_V
            if self.args.sse:
                template += '\n' + self.SSE_TEMPLATE_V

        # Process formatting settings
        data = defaultdict(lambda: '<n/a>')
        data.update(msg['data'])
        formats = self.FORMAT_INFO['x64']
        formatted = {}
        for fmt in formats:
            # Apply defaults where they're missing
            fmt = dict(self.format_defaults.items() + fmt.items())

            # Format the data for each register
            for reg in fmt['regs']:
                # Format the label
                label = fmt['label_format'].format(reg)
                if fmt['label_func'] != None:
                    formatted[reg+'l'] = fmt['label_func'](label)
                if fmt['label_colour_en']:
                    formatted[reg+'l'] =  colored(formatted[reg+'l'], fmt['label_colour'])

                # Format the value
                val = data[reg]
                if type(val) == str:
                    temp = fmt['value_format'].format(0)
                    if len(val) < len(temp):
                        val += (len(temp) - len(val))*' '
                    formatted[reg] = colored(val, fmt['value_colour'])
                else:
                    colour = fmt['value_colour']
                    if self.last_regs == None or self.last_regs != None and val != self.last_regs[reg]:
                        colour = fmt['value_colour_mod']
                    formatted[reg] = fmt['value_format'].format(val)
                    if fmt['value_func'] != None:
                        if type(fmt['value_func']) == str:
                            formatted[reg] = eval(fmt['value_func'])(formatted[reg])
                        else:
                            formatted[reg] = fmt['value_func'](formatted[reg])
                    if fmt['value_colour_en']:
                        formatted[reg] = colored(formatted[reg], colour)

        # Prepare output
        log.debug('Formatted: ' + str(formatted))
        self.title = '[regs]'
        self.body = template.format(**formatted)

        # Pad
        lines = self.body.split('\n')
        pad = self.body_height() - len(lines)
        if pad < 0:
            pad = 0
        self.body += pad*'\n'

        # Store the regs
        self.last_regs = data

        # Call parent's render method
        super(RegisterView, self).render()

    def format_flags(self, val):
        values = {}

        # Get formatting info for flags
        fmt = dict(self.format_defaults.items() + filter(lambda x: 'rflags' in x['regs'], self.FORMAT_INFO['x64'])[0].items())

        # Handle each flag bit
        val = int(val, 10)
        formatted = {}
        for flag in self.FLAG_BITS.keys():
            values[flag] = (val & (1 << self.FLAG_BITS[flag]) > 0)
            log.debug("Flag {} value {} (for rflags 0x{})".format(flag, values[flag], val))
            formatted[flag] = str.upper(flag) if values[flag] else flag
            if self.last_flags != None and self.last_flags[flag] != values[flag]:
                colour = fmt['value_colour_mod']
            else:
                colour = fmt['value_colour']
            formatted[flag] = colored(formatted[flag], colour)

        # Store the flag values for comparison
        self.last_flags = values

        # Format with template
        return self.FLAG_TEMPLATE.format(**formatted)


class DisasmView (TerminalView):
    DISASM_SHOW_LINES = 16
    DISASM_SEP_WIDTH = 90

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('disasm', help='disassembly view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=DisasmView)

    def setup(self):
        self.config['type'] = 'disasm'

    def render(self, msg=None):
        height, width = self.window_size()

        # Get the disasm
        disasm = msg['data']
        disasm = '\n'.join(disasm.split('\n')[:self.body_height()])

        # Pygmentize output
        if have_pygments:
            try:
                lexer = pygments.lexers.get_lexer_by_name('gdb')
                disasm = pygments.highlight(disasm, lexer, pygments.formatters.Terminal256Formatter())
            except Exception as e:
                log.warning('Failed to highlight disasm: ' + str(e))

        # Build output
        self.title = '[code]'
        self.body = disasm.rstrip()

        # Call parent's render method
        super(DisasmView, self).render()
    

class StackView (TerminalView):
    STACK_SHOW_LINES = 16
    STACK_SEP_WIDTH = 90

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('stack', help='stack view')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('--bytes', '-b', action='store', type=int, help='bytes per line (default 16)', default=16)
        sp.set_defaults(func=StackView)

    def setup(self):
        self.config['type'] = 'stack'

    def render(self, msg=None):
        height, width = self.window_size()

        # Get the stack data
        data = msg['data']
        stack_raw = data['data']
        sp = data['sp']
        stack_raw = stack_raw[:(self.body_height())*self.args.bytes]

        # Hexdump it
        lines = self.hexdump(stack_raw, offset=sp, length=self.args.bytes).split('\n')
        lines.reverse()
        stack = '\n'.join(lines)

        # Build output
        self.title = "[stack]"
        self.info = '[0x{0:0=4x}:'.format(len(stack_raw)) + ADDR_FORMAT_64.format(sp) + ']'
        self.body = stack.strip()

        # Call parent's render method
        super(StackView, self).render()


class BacktraceView (TerminalView):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('bt', help='backtrace view')
        VoltronView.add_generic_arguments(sp)
        sp.set_defaults(func=BacktraceView)

    def setup(self):
        self.config['type'] = 'bt'

    def render(self, msg=None):
        height, width = self.window_size()

        # Get the back trace data
        data = msg['data']
        lines = data.split('\n')
        pad = self.body_height() - len(lines) + 1
        if pad < 0:
            pad = 0

        # Build output
        self.title = '[backtrace]'
        self.body = data.strip() + pad*'\n'

        # Call parent's render method
        super(BacktraceView, self).render()


class CommandView (TerminalView):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('cmd', help='command view - specify a command to be run each time the debugger stops')
        VoltronView.add_generic_arguments(sp)
        sp.add_argument('command', action='store', help='command to run')
        sp.set_defaults(func=CommandView)

    def setup(self):
        self.config['type'] = 'cmd'
        self.config['cmd'] = self.args.command

    def render(self, msg=None):
        # Get the command output
        data = msg['data']
        lines = data.split('\n')
        pad = self.body_height() - len(lines) + 1
        if pad < 0:
            pad = 0

        # Build output
        self.title = '[cmd:' + self.config['cmd'] + ']'
        self.body = data.rstrip() + pad*'\n'

        # Call parent's render method
        super(CommandView, self).render()


# This class is called from the command line by GDBv6's stop-hook. The dumped registers and stack are collected,
# parsed and sent to the voltron standalone server, which then sends the updates out to any registered clients.
# I hate that this exists. Fuck GDBv6.
class GDB6Proxy (asyncore.dispatcher):
    REGISTERS = ['rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','rip','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cs','ds','es','fs','gs','ss']

    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('gdb6proxy', help='import a dump from GDBv6 and send it to the server')
        sp.add_argument('type', action='store', help='the type to proxy - reg or stack')
        sp.set_defaults(func=GDB6Proxy)

    def __init__(self, args={}):
        global log
        asyncore.dispatcher.__init__(self)
        self.args = args
        if not args.debug:
            log.setLevel(logging.WARNING)
        self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connect(SOCK)

    def run(self):
        asyncore.loop()

    def handle_connect(self):
        if self.args.type == "reg":
            event = self.read_registers()
        elif self.args.type == "stack":
            event = self.read_stack()
        else:
            log.error("Invalid proxy type")
        log.debug("Pushing update to server")
        log.debug(str(event))
        self.send(pickle.dumps(event))

    def handle_read(self):
        data = self.recv(READ_MAX)
        msg = pickle.loads(data)
        if msg['msg_type'] != 'ack':
            log.error("Did not get ack: " + str(msg))
        self.close()

    def read_registers(self):
        log.debug("Parsing register data")
        data = {}
        for reg in GDB6Proxy.REGISTERS:
            try:
                with open('/tmp/voltron.reg.'+reg, 'r+b') as f:
                    if reg in ['eflags','cs','ds','es','fs','gs','ss']:
                        (val,) = struct.unpack('<L', f.read())
                    else:
                        (val,) = struct.unpack('<Q', f.read())
                data[reg] = val
            except Exception as e:
                log.warning("Exception reading register {}: {}".format(reg, str(e)))
                data[reg] = '<fail>'
        data['rflags'] = data['eflags']
        event = {'msg_type': 'push_update', 'update_type': 'register', 'data': data}
        return event

    def read_stack(self):
        log.debug("Parsing stack data")
        with open('/tmp/voltron.stack', 'r+b') as f:
            data = f.read()
        with open('/tmp/voltron.reg.rsp', 'r+b') as f:
            (rsp,) = struct.unpack('<Q', f.read())
        event = {'msg_type': 'push_update', 'update_type': 'stack', 'data': {'sp': rsp, 'data': data}}
        return event

    def cleanup(self):
        pass


if __name__ == "__main__":
    main()
