try:
    import logging
    blessed = None
    import blessed

    import voltron
    from voltron.core import Server
    from voltron.plugin import PluginManager
    try:
        import lldb
        in_lldb = True
    except ImportError:
        in_lldb = False
    try:
        import gdb
        in_gdb = True
    except ImportError:
        in_gdb = False

    if "vtrace" in locals():
        in_vdb = True

        import os
        import sys

        def parent_directory(the_path):
            return os.path.abspath(os.path.join(the_path, os.pardir))

        def add_vdb_to_path(vtrace):
            sys.path.append(parent_directory(parent_directory(vtrace.__file__)))

        # don't pass over this line!
        # in order for the *VDB adaptor plugin* (not this file) to import
        #  vdb stuff, the import path must be updated.
        # this is it.
        #
        # since atm vdb imports everything relatively
        #   (typically its not installed), then we use this
        #   hack to extract the package that's in use.
        add_vdb_to_path(vtrace)
        import vtrace
    else:
        in_vdb = False

    log = voltron.setup_logging('debugger')

    class VoltronCommand (object):
        """
        Parent class for common methods across all debugger hosts.
        """
        def handle_command(self, command):
            global log
            if 'debug' in command:
                if 'enable' in command:
                    log.setLevel(logging.DEBUG)
                    print("Debug logging enabled")
                elif 'disable' in command:
                    log.setLevel(logging.INFO)
                    print("Debug logging disabled")
                else:
                    enabled = "enabled" if log.getEffectiveLevel() == logging.DEBUG else "disabled"
                    print("Debug logging is currently " + enabled)
            elif 'init' in command:
                self.register_hooks()
            elif 'stopped' in command or 'update' in command:
                self.adaptor.update_state()
                self.server.dispatch_queue()
            else:
                print("Usage: voltron <init|debug|update>")

    if in_lldb:
        class VoltronLLDBCommand (VoltronCommand):
            """
            Debugger command class for LLDB
            """
            def __init__(self, debugger, dict):
                super(VoltronCommand, self).__init__()

                # grab the debugger and command interpreter
                self.debugger = debugger
                self.ci = self.debugger.GetCommandInterpreter()

                # install the voltron command handler
                self.debugger.HandleCommand('command script add -f entry.lldb_invoke voltron')

                # load plugins
                self.pm = voltron.plugin.pm

                # set up an lldb adaptor and set it as the package-wide adaptor
                self.adaptor = self.pm.debugger_plugin_for_host('lldb').adaptor_class()
                voltron.debugger = self.adaptor

                # register plugins now that we have a debugger
                self.pm.register_plugins()

                # start the server
                self.server = Server()
                self.server.start()

                self.hook_idx = None

            def invoke(self, debugger, command, result, dict):
                self.handle_command(command)

            def register_hooks(self):
                try:
                    output = self.adaptor.command("target stop-hook list")
                    if 'voltron' not in output:
                        output = self.adaptor.command('target stop-hook add -o \'voltron stopped\'')
                        try:
                            # hahaha this sucks
                            self.hook_idx = int(res.GetOutput().strip().split()[2][1:])
                        except:
                            pass
                    print("Registered stop-hook")
                except:
                    print("No targets")

            def unregister_hooks(self):
                cmd = 'target stop-hook delete {}'.format(self.hook_idx if self.hook_idx else '')
                self.debugger.HandleCommand(cmd)

        def __lldb_init_module(debugger, env_dict):
            """
            Called by LLDB when the module is loaded
            """
            if 'cmd' not in env_dict:
                log.debug("Initialising LLDB command")
                env_dict['cmd'] = VoltronLLDBCommand(debugger, env_dict)
                voltron.cmd = env_dict['cmd']
                print(blessed.Terminal().bold_red("Voltron loaded."))
                print("Run `voltron init` after you load a target.")
                env_dict['cmd'].adaptor.host.HandleCommand("script import voltron")

        def lldb_invoke(debugger, command, result, env_dict):
            """
            Called when the voltron command is invoked within LLDB
            """
            env_dict['cmd'].invoke(debugger, command, result, env_dict)

    if in_gdb:
        class VoltronGDBCommand (VoltronCommand, gdb.Command):
            """
            Debugger command class for GDB
            """
            def __init__(self):
                super(VoltronCommand, self).__init__("voltron", gdb.COMMAND_NONE, gdb.COMPLETE_NONE)

                # load plugins
                self.pm = PluginManager()

                # set up a gdb adaptor and set it as the package-wide adaptor
                self.adaptor = self.pm.debugger_plugin_for_host('gdb').adaptor_class()
                voltron.debugger = self.adaptor

                # register plugins now that we have a debugger
                self.pm.register_plugins()

                # server is started and stopped with the inferior to avoid GDB hanging on exit
                self.server = None
                self.registered = False

            def invoke(self, arg, from_tty):
                self.handle_command(arg)

            def register_hooks(self):
                if not self.registered:
                    gdb.events.stop.connect(self.stop_handler)
                    gdb.events.exited.connect(self.stop_and_exit_handler)
                    gdb.events.cont.connect(self.cont_handler)

            def unregister_hooks(self):
                if self.registered:
                    gdb.events.stop.disconnect(self.stop_handler)
                    gdb.events.exited.disconnect(self.stop_and_exit_handler)
                    gdb.events.cont.disconnect(self.cont_handler)

            def stop_handler(self, event):
                self.adaptor.update_state()
                self.server.dispatch_queue()
                log.debug('Inferior stopped')

            def exit_handler(self, event):
                log.debug('Inferior exited')
                self.server.stop()

            def stop_and_exit_handler(self, event):
                log.debug('Inferior stopped and exited')
                self.stop_handler(event)
                self.exit_handler(event)

            def cont_handler(self, event):
                log.debug('Inferior continued')
                if not self.server:
                    self.server = Server()
                    self.server.start()

        if __name__ == "__main__":
            log.debug('Initialising GDB command')
            voltron.cmd = VoltronGDBCommand()
            print(blessed.Terminal().bold_red("Voltron loaded."))

    if in_vdb:
        class VoltronVDBCommand(VoltronCommand, vtrace.Notifier):
            """
            Debugger command class for VDB
            """
            def __init__(self, vdb, vtrace):
                """
                vdb is the debugger instance
                vtrace is the vtrace module?
                """
                super(VoltronCommand, self).__init__()
                self._vdb = vdb
                self._vtrace = vtrace

                self.pm = PluginManager()

                self.adaptor = self.pm.debugger_plugin_for_host('vdb').adaptor_class(self._vdb, self._vtrace)
                voltron.debugger = self.adaptor

                self.pm.register_plugins()

                self.server = Server()
                self.server.start()

            def invoke(self, arg, from_tty):
                self.handle_command(arg)

            def register_hooks(self):
                self._vdb.registerNotifier(vtrace.NOTIFY_ALL, self)

            def unregister_hooks(self):
                self._vdb.deregisterNotifier(vtrace.NOTIFY_ALL, self)

            def notify(self, event, trace):
                if event == self._vtrace.NOTIFY_DETACH:
                    self.exit_handler(event)
                elif event == self._vtrace.NOTIFY_EXIT:
                    self.exit_handler(event)
                elif event == self._vtrace.NOTIFY_BREAK:
                    self.stop_handler(event)
                elif event == self._vtrace.NOTIFY_STEP:
                    self.stop_handler(event)
                elif event == self._vtrace.NOTIFY_CONTINUE:
                    self.cont_handler(event)

            def stop_handler(self, event):
                self.adaptor.update_state()
                log.debug('Inferior stopped')

            def exit_handler(self, event):
                log.debug('Inferior exited')
                self.server.stop()
                # vdb doesn't signal STOP/BREAK on exit, so we
                #   clear an outstanding Wait requests
                self.adaptor.update_state()

            def cont_handler(self, event):
                log.debug('Inferior continued')

        # wb: i have no idea if this __name__ test is actually correct
        # but __builtin__ is its value when run from vdbbin
        if __name__ == "__builtin__":
            log.debug('Initialising VDB command')
            inst = VoltronVDBCommand(db, vtrace)
            inst.register_hooks()
            print(blessed.Terminal().bold_red("Voltron loaded."))

except Exception as e:
    msg = "Exception {} raised while loading Voltron: {}".format(type(e), str(e))
    if blessed:
        msg = blessed.Terminal().bold_red(msg)
    print(msg)
