import logging
import inspect
import os
from collections import defaultdict

from scruffy.plugin import Plugin

import voltron

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
        self._web_plugins = defaultdict(lambda: None)
        self._command_plugins = defaultdict(lambda: None)

    def register_plugins(self):
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

    @property
    def web_plugins(self):
        return self._web_plugins

    @property
    def command_plugins(self):
        return self._command_plugins

    def register_plugin(self, plugin):
        """
        Register a new plugin with the PluginManager.

        `plugin` is a subclass of scruffy's Plugin class.

        This is called by __init__(), but may also be called by the debugger
        host to load a specific plugin at runtime.
        """
        if hasattr(plugin, 'initialise'):
            plugin.initialise()
        if self.valid_api_plugin(plugin):
            log.debug("Registering API plugin: {}".format(plugin))
            self._api_plugins[plugin.request] = plugin()
        elif self.valid_debugger_plugin(plugin):
            log.debug("Registering debugger plugin: {}".format(plugin))
            self._debugger_plugins[plugin.host] = plugin()
        elif self.valid_view_plugin(plugin):
            log.debug("Registering view plugin: {}".format(plugin))
            self._view_plugins[plugin.name] = plugin()
        elif self.valid_web_plugin(plugin):
            log.debug("Registering web plugin: {}".format(plugin))
            self._web_plugins[plugin.name] = plugin()
        elif self.valid_command_plugin(plugin):
            log.debug("Registering command plugin: {}".format(plugin))
            self._command_plugins[plugin.name] = plugin()
            if voltron.debugger:
                voltron.debugger.register_command_plugin(plugin.name, plugin.command_class)
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

    def valid_web_plugin(self, plugin):
        """
        Validate a web plugin, ensuring it is a web plugin and has the
        necessary fields present.

        `plugin` is a subclass of scruffy's Plugin class.
        """
        if (issubclass(plugin, WebPlugin)      and
            hasattr(plugin, 'plugin_type')      and plugin.plugin_type == 'web' and
            hasattr(plugin, 'name')             and plugin.name != None):
            return True
        return False

    def valid_command_plugin(self, plugin):
        """
        Validate a command plugin, ensuring it is a command plugin and has the
        necessary fields present.

        `plugin` is a subclass of scruffy's Plugin class.
        """
        if (issubclass(plugin, CommandPlugin)   and
            hasattr(plugin, 'plugin_type')      and plugin.plugin_type == 'command' and
            hasattr(plugin, 'name')             and plugin.name != None):
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
        return self.view_plugins[name]

    def web_plugin_with_name(self, name=None):
        """
        Find a web plugin that for the given view name.
        """
        return self.web_plugins[name]

    def command_plugin_with_name(self, name=None):
        """
        Find a command plugin that for the given view name.
        """
        return self.command_plugins[name]


class VoltronPlugin(Plugin):
    @classmethod
    def initialise(cls):
        pass


class APIPlugin(VoltronPlugin):
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

    @classmethod
    def initialise(cls):
        if cls.request_class:
            cls.request_class._plugin = cls
            cls.request_class.request = cls.request


class DebuggerAdaptorPlugin(VoltronPlugin):
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

    @classmethod
    def initialise(cls):
        if cls.adaptor_class:
            cls.adaptor_class._plugin = cls


class ViewPlugin(VoltronPlugin):
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

    @classmethod
    def initialise(cls):
        if cls.view_class:
            cls.view_class._plugin = cls
            cls.view_class.view_type = cls.name


class WebPlugin(VoltronPlugin):
    """
    Web plugin parent class.

    `plugin_type` is 'web'
    `name` is the name of the web plugin (e.g. 'webview')
    `app` is a Flask app (or whatever, optional)
    """
    _dir = None

    plugin_type = 'web'
    name = None
    app = None

    def __init__(self):
        self._dir = os.path.dirname(inspect.getfile(self.__class__))


class CommandPlugin(VoltronPlugin):
    """
    Command plugin parent class.

    `plugin_type` is 'command'
    `name` is the name of the command plugin
    """
    plugin_type = 'command'
    name = None


#
# Shared plugin manager and convenience methods
#

pm = PluginManager()


def api_request(request, *args, **kwargs):
    """
    Create an API request.

    `request_type` is the request type (string). This is used to look up a
    plugin, whose request class is instantiated and passed the remaining
    arguments passed to this function.
    """
    plugin = pm.api_plugin_for_request(request)
    if plugin and plugin.request_class:
        req = plugin.request_class(*args, **kwargs)
    else:
        raise Exception("Invalid request type")
    return req


def api_response(request, *args, **kwargs):
    plugin = pm.api_plugin_for_request(request)
    if plugin and plugin.response_class:
        req = plugin.response_class(*args, **kwargs)
    else:
        raise Exception("Invalid request type")
    return req


def debugger_adaptor(host, *args, **kwargs):
    plugin = pm.debugger_plugin_for_host(host)
    if plugin and plugin.adaptor_class:
        adaptor = plugin.adaptor_class(*args, **kwargs)
    else:
        raise Exception("Invalid debugger host")
    return adaptor


def view(name, *args, **kwargs):
    plugin = pm.view_plugin_with_name(name)
    if plugin and plugin.view_class:
        view = plugin.view_class(*args, **kwargs)
    else:
        raise Exception("Invalid view name")
    return view


def command(name, *args, **kwargs):
    plugin = pm.command_plugin_with_name(name)
    if plugin and plugin.command_class:
        command = plugin.command_class(*args, **kwargs)
    else:
        raise Exception("Invalid command name")
    return command


def web_plugins():
    return pm.web_plugins
