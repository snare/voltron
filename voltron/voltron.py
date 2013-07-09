#!/usr/bin/env python

import os
import argparse
import logging
import logging.config
import struct
import json

from view import *
from comms import *
from gdbproxy import *

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
            'voltron': {
                'handlers': ['default'],
                'level': 'INFO',
                'propogate': True,
            }
        }
}
logging.config.dictConfig(LOG_CONFIG)
log = logging.getLogger('voltron')

def main(debugger=None, dict=None):
    global log, queue, inst

    # Load config
    config = {}
    try:
        config_data = file(os.path.expanduser('~/.voltron')).read()
        lines = filter(lambda x: len(x) != 0 and x[0] != '#', config_data.split('\n'))
        config = json.loads('\n'.join(lines))
    except:
        log.debug("No config file")

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


