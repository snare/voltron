import logging

LOGGER_DEFAULT = {
    'handlers': ['file'],
    'level': 'DEBUG',
    'propagate': True
}

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '[%(levelname)s] %(message)s'},
        'testing': {'format': "%(levelname)-7s %(filename)12s:%(lineno)-4s %(funcName)20s -- %(message)s"}
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'class': 'logging.FileHandler',
            'formatter': 'testing',
            'filename': 'tests/test.log',
            'delay': True
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

logging.config.dictConfig(LOG_CONFIG)
