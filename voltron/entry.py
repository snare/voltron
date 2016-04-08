"""
This is the main entry point for Voltron from the debugger host's perspective.
This file is loaded into the debugger through whatever means the given host
supports.

In LLDB:

    (lldb) command script import /path/to/voltron/entry.py

In GDB:

    (gdb) source /path/to/voltron/entry.py

In VDB:

    (vdb) script /path/to/voltron/entry.py
"""

try:
    import logging
    import os
    import sys
    blessed = None
    import blessed

    import voltron
    from voltron.plugin import pm
    from voltron.core import Server

    log = voltron.setup_logging('debugger')

    # figure out in which debugger host we are running
    try:
        import lldb
        host = "lldb"
    except ImportError:
        pass
    try:
        import gdb
        host = "gdb"
    except ImportError:
        pass
    if "vtrace" in locals():
        host = "vdb"
    if not host:
        raise Exception("No debugger host is present")

    # register any plugins that were loaded
    pm.register_plugins()

    # get the debugger plugin for the host we're in
    plugin = pm.debugger_plugin_for_host(host)

    # set up command and adaptor instances
    voltron.debugger = plugin.adaptor_class()
    voltron.command = plugin.command_class()

    # create and start the voltron server
    voltron.server = Server()
    if host != "gdb":
        voltron.server.start()

    print(blessed.Terminal().bold_red("Voltron loaded."))
    if host == 'lldb':
        print("Run `voltron init` after you load a target.")

except Exception as e:
    msg = "Exception {} raised while loading Voltron: {}".format(type(e), str(e))
    if blessed:
        msg = blessed.Terminal().bold_red(msg)
    print(msg)
