import logging
from collections import defaultdict

from scruffy.plugin import Plugin

import voltron
from .common import *

log = logging.getLogger('plugin')

class PluginManager(object):
    """
    Collects and validates API, debugger and view plugins. Provides methods to
    access and search the plugin collection.

    Plugin loading itself is handled by scruffy, which is configured in the
    environment specification in `env.py`.
    """
    def __init__(self):
        """
        Initialise a new PluginManager.
        """
        self._api_plugins = defaultdict(lambda: None)
        self._debugger_plugins = defaultdict(lambda: None)
        self._view_plugins = defaultdict(lambda: None)

        log.debug("Initalising PluginManager {}".format(self))

        # register all plugins in the environment
        for p in voltron.env.plugins:
            self.register_plugin(p)

    @property
    def api_plugins(self):
        return self._api_plugins

    @property
    def debugger_plugins(self):
        return self._debugger_plugins

    @property
    def view_plugins(self):
        return self._view_plugins

    def register_plugin(self, plugin):
        """
        Register a new plugin with the PluginManager.

        `plugin` is a subclass of scruffy's Plugin class.

        This is called by __init__(), but may also be called by the debugger
        host to load a specific plugin at runtime.
        """
        if self.valid_api_plugin(plugin):
            log.debug("Registering API plugin: {}".format(plugin))

            # instantiate the API plugin, give its request class a ref to the
            # plugin, and set its request type
            p = plugin()
            p.request_class._plugin = plugin
            p.request_class._request = plugin.request
            self._api_plugins[plugin.request] = p
        elif self.valid_debugger_plugin(plugin):
            log.debug("Registering debugger plugin: {}".format(plugin))
            self._debugger_plugins[plugin.host] = plugin()
        elif self.valid_view_plugin(plugin):
            log.debug("Registering view plugin: {}".format(plugin))
            self._view_plugins[plugin.name] = plugin()
        else:
            log.debug("Ignoring invalid plugin: {}".format(plugin))

    def valid_api_plugin(self, plugin):
        """
        Validate an API plugin, ensuring it is an API plugin and has the
        necessary fields present.

        `plugin` is a subclass of scruffy's Plugin class.
        """
        if (issubclass(plugin, APIPlugin)       and
            hasattr(plugin, 'plugin_type')      and plugin.plugin_type == 'api' and
            hasattr(plugin, 'request')          and plugin.request != None and
            hasattr(plugin, 'request_class')    and plugin.request_class != None and
            hasattr(plugin, 'response_class')   and plugin.response_class != None):
            return True
        return False

    def valid_debugger_plugin(self, plugin):
        """
        Validate a debugger plugin, ensuring it is a debugger plugin and has
        the necessary fields present.

        `plugin` is a subclass of scruffy's Plugin class.
        """
        if (issubclass(plugin, DebuggerAdaptorPlugin) and
            hasattr(plugin, 'plugin_type')      and plugin.plugin_type == 'debugger' and
            hasattr(plugin, 'host')             and plugin.host != None):
            return True
        return False

    def valid_view_plugin(self, plugin):
        """
        Validate a view plugin, ensuring it is a view plugin and has the
        necessary fields present.

        `plugin` is a subclass of scruffy's Plugin class.
        """
        if (issubclass(plugin, ViewPlugin)      and
            hasattr(plugin, 'plugin_type')      and plugin.plugin_type == 'view' and
            hasattr(plugin, 'name')             and plugin.name != None and
            hasattr(plugin, 'view_class')       and plugin.view_class != None):
            return True
        return False

    def api_plugin_for_request(self, request=None):
        """
        Find an API plugin that supports the given request type.
        """
        return self.api_plugins[request]

    def debugger_plugin_for_host(self, host=None):
        """
        Find a debugger plugin that supports the debugger host.
        """
        return self.debugger_plugins[host]

    def view_plugin_with_name(self, name=None):
        """
        Find a view plugin that for the given view name.
        """
        return self.view_plugins[host]


class APIPlugin(Plugin):
    """
    Abstract API plugin class. API plugins subclass this.

    `plugin_type` is 'api'
    `request` is the request type (e.g. 'version')
    `request_class` is the APIRequest subclass (e.g. APIVersionRequest)
    `response_class` is the APIResponse subclass (e.g. APIVersionResponse)
    `supported_hosts` is an array of debugger adaptor plugins that this plugin
    supports (e.g. 'lldb', 'gdb'). There is also a special host type called
    'core' If the plugin requires only the 'core' debugger host, it can be used
    with any debugger adaptor plugin that implements the full interface (ie.
    the included 'lldb' and 'gdb' plugins). If it requires a specifically named
    debugger host plugin, then it will only work with those plugins specified.
    This allows developers to add custom API plugins that communicate directly
    with their chosen debugger host API, to do things that the standard
    debugger adaptor plugins don't support.

    See the core API plugins in voltron/plugins/api/ for examples.
    """
    plugin_type = 'api'
    request = None
    request_class = None
    response_class = None
    supported_hosts = ['core']

class DebuggerAdaptorPlugin(Plugin):
    """
    Debugger adaptor plugin parent class.

    `plugin_type` is 'debugger'
    `host` is the name of the debugger host (e.g. 'lldb' or 'gdb')
    `adaptor_class` is the debugger adaptor class that can be queried
    See the core debugger plugins in voltron/plugins/debugger/ for examples.
    """
    plugin_type = 'debugger'
    host = None
    adaptor_class = None
    supported_hosts = ['core']

class ViewPlugin(Plugin):
    """
    View plugin parent class.

    `plugin_type` is 'view'
    `name` is the name of the view (e.g. 'register' or 'disassembly')
    `view_class` is the main view class

    See the core view plugins in voltron/plugins/view/ for examples.
    """
    plugin_type = 'view'
    name = None
    view_class = None
