import os
import argparse
import logging
import traceback
import logging
import logging.config

import voltron
from .view import *
from .core import *

log = logging.getLogger('main')


def main(debugger=None):
    voltron.setup_logging('main')

    # Set up command line arg parser
    parser = argparse.ArgumentParser()
    parser.register('action', 'parsers', AliasedSubParsersAction)
    parser.add_argument('--debug', '-d', action='store_true', help='print debug logging')
    parser.add_argument('-o', action='append', help='override config variable', default=[])
    top_level_sp = parser.add_subparsers(title='subcommands', description='valid subcommands', dest='subcommand')
    top_level_sp.required = True
    view_parser = top_level_sp.add_parser('view', help='display a view', aliases=('v'))
    view_parser.register('action', 'parsers', AliasedSubParsersAction)
    view_sp = view_parser.add_subparsers(title='views', description='valid view types', help='additional help', dest='view')
    view_sp.required = True

    # Set up a subcommand for each view class
    pm = PluginManager()
    pm.register_plugins()
    for plugin in pm.view_plugins:
        pm.view_plugins[plugin].view_class.configure_subparser(view_sp)

    # Parse args
    args = parser.parse_args()
    if args.debug:
        voltron.config['general']['debug_logging'] = True
        voltron.setup_logging('main')
    voltron.config.update(options=dict((tuple(x.split('=')) for x in args.o)))

    # Instantiate and run the appropriate module
    inst = args.func(args, loaded_config=voltron.config)
    inst.pm = pm
    try:
        inst.run()
    except Exception as e:
        log.exception("Exception running module {}: {}".format(inst.__class__.__name__, traceback.format_exc()))
        print("Encountered an exception while running the view '{}':\n{}".format(inst.__class__.__name__, traceback.format_exc()))
    except KeyboardInterrupt:
        suppress_exit_log = True
    inst.cleanup()
