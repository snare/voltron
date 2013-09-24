import os
import json

VOLTRON_DIR = os.path.expanduser('~/.voltron/')
VOLTRON_CONFIG = os.path.join(VOLTRON_DIR, 'config')

def _load_config():
    try:
        config_data = file(VOLTRON_CONFIG).read()
        lines = filter(lambda x: len(x) != 0 and x[0] != '#', config_data.split('\n'))
        return json.loads('\n'.join(lines))
    except:
        log.debug("No config file")
        return {}

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
