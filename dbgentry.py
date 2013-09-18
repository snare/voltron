import voltron
import voltron.common
try:
    import voltron.lldbcmd
    in_lldb = True
except:
    in_lldb = False
try:
    import voltron.gdbcmd
    in_gdb = True
except:
    in_gdb = False

log = voltron.common.configure_logging()

if in_lldb:
    # Called when the module is loaded into lldb and initialised
    def __lldb_init_module(debugger, dict):
        log.debug("Initialising LLDB command")
        voltron.lldbcmd.inst = voltron.lldbcmd.VoltronLLDBCommand(debugger, dict)

    # Called when the command is invoked by lldb
    def lldb_invoke(debugger, command, result, dict):
        voltron.lldbcmd.inst.invoke(debugger, command, result, dict)

if in_gdb:
    # Called when the module is loaded by gdb
    if __name__ == "__main__":
        log.debug('Initialising GDB command')
        print("Voltron loaded.")
        inst = voltron.gdbcmd.VoltronGDBCommand()

if not in_lldb and not in_gdb:
    print("Something wicked this way comes")
