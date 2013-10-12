import os
import json
import pkg_resources

from .common import *

log = configure_logging()

VOLTRON_DIR = os.path.expanduser('~/.voltron/')
VOLTRON_CONFIG = os.path.join(VOLTRON_DIR, 'config')
DEFAULT_CONFIG = 'config/default.cfg'

def _parse_config(config):
    lines = filter(lambda x: len(x) != 0 and x.strip()[0] != '#', config.split('\n'))
    return json.loads('\n'.join(lines))

def _load_config():
    # load default config
    try:
        config = _parse_config(pkg_resources.resource_string('voltron', DEFAULT_CONFIG))
    except Exception, e:
        raise IOError("No default configuration found. Your package is probably broken: " + str(e))

    # load local config
    try:
        local_config = _parse_config(file(VOLTRON_CONFIG).read())
        config = merge(local_config, config)
    except:
        raise
        pass

    # parse json
    return config

CONFIG = _load_config()

def _voltron_basename():
    SOCKET_LENGTH = 16
    default = "voltron"
    try:
        name = os.getenv(CONFIG['main']['basename_variable'])
        name = name.replace("/", '')
        if len(name) > SOCKET_LENGTH:
            return name[-SOCKET_LENGTH:]
        else:
            return name
    except:
        return default

VOLTRON_BASENAME = _voltron_basename()

def _voltron_socket():
    if "VOLTRON_SOCKET" in os.environ:
        return os.getenv("VOLTRON_SOCKET")
    else:
        d = VOLTRON_DIR
        if not os.path.exists(d):
            os.mkdir(d, 0700)
        return os.path.join(d, "%s.sock" % VOLTRON_BASENAME)

VOLTRON_SOCKET = _voltron_socket()
