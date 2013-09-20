#!/usr/bin/env python

import os
import argparse
import logging
import logging.config
import struct
import json

from .view import *
from .comms import *
from .gdbproxy import *
from .common import *

log = configure_logging()

def main(debugger=None, dict=None):
    global log, queue, inst

    # Load config
    config = {}
    try:
        config_data = file(VOLTRON_CONFIG).read()
        lines = filter(lambda x: len(x) != 0 and x[0] != '#', config_data.split('\n'))
        config = json.loads('\n'.join(lines))
    except:
        log.debug("No config file")

    # Set up command line arg parser
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true', help='print debug logging')
    top_level_sp = parser.add_subparsers(title='subcommands', description='valid subcommands')
    view_parser = top_level_sp.add_parser('view', help='display a view')
    view_sp = view_parser.add_subparsers(title='views', description='valid view types', help='additional help')

    # Update the view base class
    base = CursesView if 'curses' in config.keys() and config['curses'] else TerminalView
    for cls in TerminalView.__subclasses__():
        cls.__bases__ = (base,)

    # Set up a subcommand for each view class
    for cls in base.__subclasses__():
        cls.configure_subparser(view_sp)

    # And subcommands for the loathsome red-headed stepchildren
    StandaloneServer.configure_subparser(top_level_sp)
    GDB6Proxy.configure_subparser(top_level_sp)

    # Parse args
    args = parser.parse_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    # Instantiate and run the appropriate module
    inst = args.func(args, loaded_config=config)
    try:
        inst.run()
    except Exception as e:
        log.error("Exception running module {}: {}".format(inst.__class__.__name__, str(e)))
    except KeyboardInterrupt:
        pass
    inst.cleanup()
    log.info('Exiting')


if __name__ == "__main__":
    main()


