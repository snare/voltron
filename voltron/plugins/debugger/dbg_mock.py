from voltron.plugin import *
from voltron.dbg import *


class MockAdaptor(DebuggerAdaptor):
    pass


class MockAdaptorPlugin(DebuggerAdaptorPlugin):
    host = 'mock'
    adaptor_class = MockAdaptor
