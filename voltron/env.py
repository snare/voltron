from scruffy import Environment

from .common import *

log = configure_logging()


ENV = Environment({
    'dir':  {
        'path': '~/.voltron',
        'create': True,
        'mode': 0700
    },
    'files': {
        'config': {
            'type':     'config',
            'default':  {
                'path':     'config/default.cfg',
                'rel_to':   'pkg',
                'pkg':      'voltron'
            },
            'read':     True
        },
        'sock': {
            'name':     '{basename}.sock',
            'type':     'raw',
            'var':      'VOLTRON_SOCKET'
        },
        'history': {
            'type':     'raw',
            'var':      'VOLTRON_HISTORY'
        }
    },
    'basename': 'voltron'
})

CONFIG = ENV['config']
