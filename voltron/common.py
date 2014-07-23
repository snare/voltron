import os
import logging
import logging.config

LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'standard': {'format': 'voltron: [%(levelname)s] %(message)s'},
        'verbose': {'format': "%(levelname)-7s %(filename)12s:%(lineno)-4s %(funcName)20s -- %(message)s"}
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'debug_file': {
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
            'filename': 'voltron.debug.' + str(os.getpid()),
            'delay': True
        }
    },
    'loggers': {
        '': {
            'handlers': ['default', 'debug_file'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}

def configure_logging():
    logging.config.dictConfig(LOG_CONFIG)

class DebugOnlyFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.DEBUG

class DebugMaxFilter(logging.Filter):
    def filter(self, record):
        return record.levelno > logging.DEBUG

def merge(d1, d2):
    for k1,v1 in d1.items():
        if isinstance(v1, dict) and k1 in d2.keys() and isinstance(d2[k1], dict):
            merge(v1, d2[k1])
        else:
            d2[k1] = v1
    return d2

# Python 3 shims
if not hasattr(__builtins__, "xrange"):
    xrange = range
