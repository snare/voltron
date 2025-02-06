"""
This is the main entry point for Voltron from the debugger host's perspective.
This file is loaded into the debugger through whatever means the given host
supports.

LLDB:

    (lldb) command script import /path/to/voltron/entry.py

GDB:

    (gdb) source /path/to/voltron/entry.py

VDB:

    (vdb) script /path/to/voltron/entry.py

WinDbg/CDB (via PyKD):

    > .load pykd.pyd
    > !py --global C:\\path\\to\\voltron\\entry.py
"""

log = None

try:
    # fix path if it's clobbered by brew
    import sys
    if sys.platform == 'darwin':
        py_base = '/System/Library/Frameworks/Python.framework/Versions/2.7/'
        new_path = ['lib/python27.zip', 'lib/python2.7', 'lib/python2.7/plat-darwin', 'lib/python2.7/plat-mac',
                    'lib/python2.7/plat-mac/lib-scriptpackages', 'Extras/lib/python', 'lib/python2.7/lib-tk',
                    'lib/python2.7/lib-old', 'lib/python2.7/lib-dynload']
        sys.path = [p for p in sys.path if 'Cellar' not in p] + [py_base + p for p in new_path]
except:
    pass

try:
    import os
    import sys
    blessed = None
    import blessed

    # add vtrace to the path so that dbg_vdb.py can import from vdb/vtrace.
    if "vtrace" in locals():
        def parent_directory(the_path):
            return os.path.abspath(os.path.join(the_path, os.pardir))

        def add_vdb_to_path(vtrace):
            sys.path.append(parent_directory(parent_directory(vtrace.__file__)))

        add_vdb_to_path(vtrace)
    else:
        pass

    import voltron
    from voltron.plugin import pm
    from voltron.core import Server

    log = voltron.setup_logging('debugger')

    # figure out in which debugger host we are running
    args = []
    host = None
    try:
        import lldb
        host = "lldb"

        def invoke(*args):
            voltron.command._invoke(*args)
    except ImportError:
        pass
    try:
        import gdb
        host = "gdb"
    except ImportError:
        pass
    try:
        import pykd
        host = "windbg"
    except:
        pass
    if "vtrace" in locals():
        host = "vdb"
        args = [db]
    if not host:
        raise Exception("No debugger host is present")

    # register any plugins that were loaded
    pm.register_plugins()

    # get the debugger plugin for the host we're in
    plugin = pm.debugger_plugin_for_host(host)

    if not voltron.server:
        # set up command and adaptor instances
        voltron.debugger = plugin.adaptor_class(*args)
        voltron.command = plugin.command_class(*args)

        # register command plugins now that we have a debugger host loaded
        pm.register_command_plugins()

        # create and start the voltron server
        voltron.server = Server()
        voltron.server.start()

        print(blessed.Terminal().bold_red("Voltron loaded."))
        if host == 'lldb' and not voltron.command.registered:
            print("Run `voltron init` after you load a target.")
except Exception as e:
    import traceback
    msg = ("An error occurred while loading Voltron:\n\n{}"
           "\nPlease ensure Voltron is installed correctly per the documentation: "
           "https://github.com/snare/voltron/wiki/Installation").format(traceback.format_exc())
    if 'blessed' in globals() and blessed:
        msg = blessed.Terminal().bold_red(msg)
    if log:
        log.exception("Exception raised while loading Voltron")
    print(msg)
