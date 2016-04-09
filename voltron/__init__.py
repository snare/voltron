import os
import logging
import logging.config

import voltron
from .main import main

from scruffy import Environment, Directory, File, ConfigFile, PluginDirectory, PackageDirectory

# scruffy environment containing config, plugins, etc
env = None
config = None

debugger = None
command = None
commands = None
server = None

loaded = False


def setup_env():
    global env, config
    env = Environment(setup_logging=False,
        voltron_dir=Directory('~/.voltron', create=True,
            config=ConfigFile('config', defaults=File('config/default.cfg', parent=PackageDirectory()), apply_env=True),
            sock=File('{config:server.listen.domain}'),
            history=File('history'),
            user_plugins=PluginDirectory('plugins')
        ),
        pkg_plugins=PluginDirectory('plugins', parent=PackageDirectory())
    )
    config = env.config

    voltron.plugin.pm.register_plugins()

LOGGER_DEFAULT = {
    'handlers': ['null'],
    'level': 'DEBUG',
    'propagate': False
}

LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'standard': {'format': 'voltron: [%(levelname)s] %(message)s'}
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'null': {
            'class': 'logging.NullHandler'
        }
    },
    'loggers': {
        '':         LOGGER_DEFAULT,
        'debugger': LOGGER_DEFAULT,
        'core':     LOGGER_DEFAULT,
        'main':     LOGGER_DEFAULT,
        'api':      LOGGER_DEFAULT,
        'view':     LOGGER_DEFAULT,
        'plugin':   LOGGER_DEFAULT,
    }
}


def setup_logging(logname=None):
    # configure logging
    logging.config.dictConfig(LOG_CONFIG)

    # enable the debug_file in all the loggers if the config says to
    if config and 'general' in config and config['general']['debug_logging']:
        if logname:
            filename = '{}.log'.format(logname)
        else:
            filename = 'voltron.log'
        for name in LOG_CONFIG['loggers']:
            h = logging.FileHandler(voltron.env.voltron_dir.path_to(filename), delay=True)
            h.setFormatter(logging.Formatter(fmt="%(asctime)s %(levelname)-7s %(filename)12s:%(lineno)-4s %(funcName)20s -- %(message)s"))
            logging.getLogger(name).addHandler(h)

    logging.info("======= VOLTRON - DEFENDER OF THE UNIVERSE [debug log] =======")

    return logging.getLogger(logname)


# Python 3 shim
if not hasattr(__builtins__, "xrange"):
    xrange = range


# Setup the Voltron environment
setup_env()
