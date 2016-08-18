Voltron
=======

[![build](https://travis-ci.org/snare/voltron.svg?branch=master)](https://travis-ci.org/snare/voltron/)

Voltron is an extensible debugger UI toolkit written in Python. It aims to improve the user experience of various debuggers (LLDB, GDB, VDB and WinDbg) by enabling the attachment of utility views that can retrieve and display data from the debugger host. By running these views in other TTYs, you can build a customised debugger user interface to suit your needs.

Voltron does not aim to be everything to everyone. It's not a wholesale replacement for your debugger's CLI. Rather, it aims to complement your existing setup and allow you to extend your CLI debugger as much or as little as you like. If you just want a view of the register contents in a window alongside your debugger, you can do that. If you want to go all out and have something that looks more like OllyDbg, you can do that too.

Built-in views are provided for:

- Registers
- Disassembly
- Stack
- Memory
- Breakpoints
- Backtrace

The author's setup looks something like this:

![voltron example LLDB](http://i.imgur.com/p3XcagJ.png)

Any debugger command can be split off into a view and highlighted with a specified Pygments lexer:

![command views](http://i.imgur.com/mqptE3Z.png)

More screenshots are [here](https://github.com/snare/voltron/wiki/Screenshots).

Support
-------

`voltron` supports LLDB, GDB, VDB and WinDbg/CDB (via [PyKD](https://pykd.codeplex.com/)) and runs on macOS, Linux and Windows.

WinDbg support is new, please [open an issue](https://github.com/snare/voltron/issues) if you have problems.

The following architectures are supported:

|         | lldb | gdb | vdb | windbg |
|---------|------|-----|-----|--------|
| x86     | ✓    | ✓   | ✓   | ✓      |
| x86_64  | ✓    | ✓   | ✓   | ✓      |
| arm     | ✓    | ✓   | ✓   | ✗      |
| arm64   | ✓    | ✗   | ✗   | ✗      |
| powerpc | ✗    | ✓   | ✗   | ✗      |

Installation
------------

Releases are on PyPI. Install with `pip`:

    $ pip install voltron

Voltron needs to be installed using the version of Python that your debugger is linked with. If Voltron cannot be loaded after installing it with the `pip` in your path, you probably have multiple versions of Python installed. See the more detailed [installation documentation](https://github.com/snare/voltron/wiki/Installation) for more info.

Quick Start
-----------

1. If your debugger has an init script (`.lldbinit` for LLDB or `.gdbinit` for GDB) configure it to load Voltron when it starts by sourcing the `entry.py` entry point script. The full path will be inside the `voltron` package. For example, on macOS it might be */Library/Python/2.7/site-packages/voltron/entry.py*. If you don't add this to your init script, you'll need to execute the commands after starting your debugger.

    LLDB:

        command script import /path/to/voltron/entry.py

    GDB:

        source /path/to/voltron/entry.py
        voltron init
        set disassembly-flavor intel

2. Start your debugger and initialise Voltron manually if necessary.

    On recent versions of LLDB you do not need to initialise Voltron manually:

        $ lldb target_binary

    On older versions of LLDB you need to call `voltron init` after you load the inferior:

        $ lldb target_binary
        (lldb) voltron init

    GDB:

        $ gdb target_binary

    VDB:

        $ ./vdbbin target_binary
        > script /path/to/voltron/entry.py

    WinDbg/CDB (requires [PyKD](https://pykd.codeplex.com/)):

        > cdb -c '.load C:\path\to\pykd.pyd ; !py --global C:\path\to\voltron\entry.py' target_binary

3. In another terminal (I use iTerm panes) start one of the UI views. On LLDB and WinDbg the views will update immediately. On GDB and VDB they will not update until the inferior stops (at a breakpoint, after a step, etc):

        $ voltron view register
        $ voltron view stack
        $ voltron view disasm
        $ voltron view backtrace

4. Set a breakpoint and run your inferior.

        (*db) b main
        (*db) run

5. When the debugger hits the breakpoint, the views will be updated to reflect the current state of registers, stack, memory, etc. Views are updated after each command is executed in the debugger CLI, using the debugger's "stop hook" mechanism. So each time you step, or continue and hit a breakpoint, the views will update.

Documentation
-------------

See the [wiki](https://github.com/snare/voltron/wiki) on github.

FAQ
---

**Q.** Why am I getting an `ImportError` loading Voltron?

**A.** You might have multiple versions of Python installed and have installed Voltron using the wrong one. See the more detailed [installation instructions](https://github.com/snare/voltron/wiki/Installation).

**Q.** Why do the views just say "Connection refused"?

**A.** Due to a limitation in the GDB API, Voltron starts and stops the webserver when the inferior starts and stops when running with GDB. Set a breakpoint and run the inferior, and the views will connect and update upon the breakpoint being hit.

Bugs and Errata
---------------

See the [issue tracker](https://github.com/snare/voltron/issues) on github for more information or to submit issues.

If you're experiencing an `ImportError` loading Voltron, please ensure you've followed the [installation instructions](https://github.com/snare/voltron/wiki/Installation) for your platform.

### GDB

1. There is no clean way to hook GDB's exit, only the inferior's exit, so the Voltron server is started and stopped along with the inferior. This results in views showing "Connection refused" before the inferior has been started.

2. Due to a limitation in the GDB API, the views are only updated each time the debugger is stopped (e.g. by hitting a breakpoint), so view contents are not populated immediately when the view is connected, only when the first breakpoint is hit.

3. If the stack view is causing GDB to hang then it must be launched **after** the debugger has been launched, the inferior started, and the debugger stopped (e.g. a breakpoint hit). This has been fixed, but this note will remain until another release is issued.

### LLDB

On older versions of LLDB, the `voltron init` command must be run manually after loading the debug target, as a target must be loaded before Voltron's hooks can be installed. Voltron will attempt to automatically register its event handler, and it will inform the user if `voltron init` is required.

### WinDbg

More information about WinDbg/CDB support [here](https://github.com/snare/voltron/wiki/Installation#windbg).

### Misc

1. The authors primarily use Voltron with the most recent version of LLDB on macOS. We will try to test everything on as many platforms and architectures as possible before releases, but LLDB/macOS/x64 is going to be by far the most frequently-used combination. Hopefully Voltron doesn't set your pets on fire, but YMMV.

2. Intel is the only disassembly flavour currently supported for syntax highlighting.

License
-------

See the [LICENSE](https://github.com/snare/voltron/blob/master/LICENSE) file.

If you use this and don't hate it, buy me a beer at a conference some time. This license also extends to other contributors - [richo](http://github.com/richo) definitely deserves a few beers for his contributions.

Credits
-------

Thanks to Azimuth Security for letting me spend time working on this.

Props to [richo](http://github.com/richo) for all his contributions to Voltron.

[fG!](http://github.com/gdbinit)'s gdbinit was the original inspiration for this project.

Thanks to [Willi](http://github.com/williballenthin) for implementing the VDB support.

Voltron now uses [Capstone](http://www.capstone-engine.org) for disassembly as well as the debugger hosts' internal disassembly mechanism. [Capstone](http://www.capstone-engine.org) is a powerful, open source, multi-architecture disassembler upon which the next generation of reverse engineering and debugging tools are being built. Check it out.
