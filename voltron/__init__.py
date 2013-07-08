import logging
import logging.config

from cmd import *
from comms import *
from view import *
from voltron import *

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
