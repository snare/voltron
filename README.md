Voltron
=======

Voltron is an extensible debugger UI toolkit written in Python. It aims to improve the user experience of various debuggers (LLDB, GDB and VDB) by enabling the attachment of utility views that can retrieve and display data from the debugger host. By running these views in other TTYs, you can build a customised debugger user interface to suit your needs.

Voltron does not aim to be everything to everyone. It's not a wholesale replacement for your debugger's CLI. Rather, it aims to complement your existing setup and allow you to extend your CLI debugger as much or as little as you like. If you just want a view of the register contents in a window alongside your debugger, you can do that. If you want to go all out and have something that looks more like OllyDbg, Immmunity Debugger, or another GUI debugger of choice, you can do that too.

Built-in views are provided for:

- Registers
- Disassembly
- Stack
- Memory
- Breakpoints
- Backtrace

The author's setup looks something like this:

![voltron example LLDB](http://i.imgur.com/p3XcagJ.png)

Support
-------

`voltron` supports LLDB, GDB and VDB. Support for WinDbg (via PyKD) is in progress.

The following architectures are supported:

|         | lldb | gdb | vdb |
|---------|------|-----|-----|
| x86     | ✓    | ✓   | ✓   |
| x86_64  | ✓    | ✓   | ✓   |
| arm     | ✓    | ✓   | ✓   |
| arm64   | ✓    | x   | x   |
| powerpc | x    | ✓   | x   |

Installation
------------

Releases are on PyPI. Install with `pip`:

    $ pip install voltron

If you want to be bleeding edge, clone this repo and install with `setup.py`:

    $ python setup.py install

Quick Start
-----------

1. Configure your debugger to load Voltron when it starts by sourcing the `entry.py` entry point script. The full path will be inside the `voltron` package. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron/entry.py*.

    For LLDB:

        command script import /path/to/voltron/entry.py

    For GDB:

        source /path/to/voltron/entry.py
        voltron init
        set disassembly-flavor intel

    VDB:

        script /path/to/voltron/entry.py

    This part can go in your `.lldbinit` or `.gdbinit` so it's automatically executed when the debugger starts.

2. Start your debugger. On LLDB you need to call `voltron init` after you load the inferior.

        $ lldb file_to_debug
        (lldb) voltron init

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view register
        $ voltron view stack
        $ voltron view disassembly
        $ voltron view backtrace

4. Set a breakpoint and run your inferior. Once the inferior has started and the debugger has stopped (either because you interrupted it or because it hit a breakpoint) the views will update.

        (*db) b main
        (*db) run

5. When the debugger hits the breakpoint, the views will be updated to reflect the current state of registers, stack, memory, etc. Views are updated after each command is executed in the debugger CLI, using the debugger's "stop hook" mechanism. So each time you step, or continue and hit a breakpoint, the views will update. A forced update can be triggered with the following command:

        (lldb) voltron update

Documentation
-------------

See the [wiki](https://github.com/snare/voltron/wiki) on github.

Bugs and Errata
---------------

See the [issue tracker](https://github.com/snare/voltron/issues) on github for more information or to submit issues.

### GDB

1. GDB on some distros is built with Python 3, but the system's Python is version 2. If Voltron is installed into Python 2's `site-packages` it will not work with GDB. See [this page on the wiki](https://github.com/snare/voltron/wiki/Voltron-on-Ubuntu-14.04-with-GDB) for installation instructions.

2. There is no clean way to hook GDB's exit, only the inferior's exit, so the Voltron server is started and stopped along with the inferior. This results in views showing "Connection refused" before the inferior has been started.

3. Due to a limitation in the GDB API, the views are only updated each time the debugger is stopped (e.g. by hitting a breakpoint), so view contents are not populated immediately when the view is connected, only when the first breakpoint is hit.

4. If the stack view is causing GDB to hang then it must be launched **after** the debugger has been launched, the inferior started, and the debugger stopped (e.g. a breakpoint hit). This is due to a GDB bug that has not yet been resolved.

### LLDB

1. The `voltron init` command must be run manually after loading the debug target, as a target must be loaded before Voltron's hooks can be installed. This means `voltron init` cannot be called from `.lldbinit` the way it can from `.gdbinit`. Hopefully this will be remedied with a more versatile hooking mechanism in a future version of LLDB (this has been discussed with the developers).

### Misc

1. Intel is the only disassembly flavour currently supported for syntax highlighting.

License
-------

See the LICENSE file.

If you use this and don't hate it, buy me a beer at a conference some time. This license also extends to other contributors - [richo](http://github.com/richo) definitely deserves a few beers for his contributions.

Credits
-------

Thanks to Azimuth Security for letting me spend time working on this.

Props to [richo](http://github.com/richo) for all his contributions to Voltron.

[fG!](http://github.com/gdbinit)'s gdbinit was the original inspiration for this project.

Thanks to [Willi](http://github.com/williballenthin) for implementing the VDB support.

Voltron now uses [Capstone](http://www.capstone-engine.org) for disassembly as well as the debugger hosts' internal disassembly mechanism. [Capstone](http://www.capstone-engine.org) is a powerful, open source, multi-architecture disassembler upon which the next generation of reverse engineering and debugging tools are being built. Check it out.