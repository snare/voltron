from __future__ import print_function

import sys
import os
import sys
import lldb
import rl
import logging
from rl import completer, generator, completion

from .core import *
from .colour import *

VERSION = 'voltron-0.1'
BANNER = "{version} (based on {lldb_version})"

log = logging.getLogger(__name__)

class Console(object):
    @classmethod
    def configure_subparser(cls, subparsers):
        sp = subparsers.add_parser('console', help='voltron debugger console')
        sp.set_defaults(func=Console)

    def __init__(self, args={}, loaded_config={}):
        self.args = args
        self.config = loaded_config['console']
        if not args.debug:
            log.setLevel(logging.WARNING)

        # set up line editor
        completer.completer = self.complete
        completer.parse_and_bind('TAB: complete')
        rl.history.read_file(voltron.env['history'])
        self.lastbuf = None

        # set up plugin manager
        self.pm = PluginManager()

        # set up debugger
        plugin = self.pm.debugger_plugin_for_host('lldb')
        self.adaptor = plugin.adaptor_class()
        self.dbg = self.adaptor.host

        # set up lldb command interpreter
        self.ci = self.adaptor.host.GetCommandInterpreter()

        # set up voltron server
        self.server = Server(debugger=self.adaptor)
        self.server.start()

        # set up voltron console command
        # self.cmd = VoltronLLDBConsoleCommand()
        # self.cmd.server = self.server
        # voltron.lldbcmd.inst = self.cmd

        # set prompt
        self.update_prompt()

    def run(self):
        # print banner
        self.print_banner()

        # main event loop
        while 1:
            try:
                self.pre_prompt()
                line = raw_input(self.prompt.encode(sys.stdout.encoding))
            except EOFError:
                break
            self.handle_command(line)
            rl.readline.write_history_file(voltron.env['history'])

    def print_banner(self):
        d = {'version': VERSION, 'lldb_version': self.dbg.GetVersionString()}
        print(BANNER.format(**d))

    def update_prompt(self):
        self.prompt = self.process_prompt(self.config['prompt'])

    def process_prompt(self, prompt):
        d = FMT_ESCAPES
        # if self.server.helper:
        #     d['pc'] = self.server.helper.get_pc()
        #     d['thread'] = self.server.helper.get_current_thread()
        # else:
        d['pc'] = 0
        d['thread'] = '-'
        return self.escape_prompt(prompt['format'].format(**d))

    def escape_prompt(self, prompt, start = "\x01", end = "\x02"):
        escaped = False
        result = ""
        for c in prompt:
            if c == "\x1b" and not escaped:
                result += start + c
                escaped = True
            elif c.isalpha() and escaped:
                result += c + end
                escaped = False
            else:
                result += c
        return result

    def pre_prompt(self):
        log.debug("updating views")
        self.update_prompt()
        # self.cmd.update()

    def handle_command(self, cmd):
        if cmd.startswith('voltron'):
            # execute voltron command
            self.cmd.handle_command(cmd)
        else:
            # execute lldb command
            res = lldb.SBCommandReturnObject()
            self.ci.HandleCommand(cmd, res)

            # print output
            if res.Succeeded():
                print(res.GetOutput().strip())
            else:
                print(res.GetError().strip())

    def complete(self, prefix, state):
        completion.suppress_append = True   # lldb appends its own spaces
        buf = rl.readline.get_line_buffer()

        if self.lastbuf != buf:
            # new buffer, redo completion
            self.res = []
            matches = lldb.SBStringList()
            r = self.ci.HandleCompletion(buf, completion.rl_point, completion.rl_point, -1, matches)
            log.debug("completion: got matches: " + str([matches.GetStringAtIndex(i) for i in range(matches.GetSize())]))

            # if there's a single fragment
            if len(matches.GetStringAtIndex(0).strip()) > 0:
                # add it
                match = prefix + matches.GetStringAtIndex(0)
                log.debug("completion: partial: " + match)
                self.res.append(match)
            else:
                # otherwise, add the other possible matches
                for i in range(1, matches.GetSize()):
                    match = matches.GetStringAtIndex(i)[len(buf.split()[-1]):]
                    self.res.append(match)

            # store buffer
            self.lastbuf = buf

        log.debug("completion: returning: " + self.res[state])
        return self.res[state]

    def cleanup(self):
        self.server.stop()

