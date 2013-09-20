import os
import logging
import logging.config

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

VOLTRON_DIR = os.path.expanduser('~/.voltron/')
VOLTRON_CONFIG = os.path.join(VOLTRON_DIR, 'config')

def configure_logging():
    logging.config.dictConfig(LOG_CONFIG)
    log = logging.getLogger('voltron')
    return log
