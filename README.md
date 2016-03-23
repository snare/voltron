Voltron
=======

Voltron is an extensible debugger interface written in Python. It allows you to attach utility views to your debugger (LLDB, GDB or VDB) that can retrieve and display data from the debugger host. By running these views in other terminal windows or panes, you can build a customised debugger user interface to suit your needs.

Built-in views are provided for:

- Registers
- Disassembly
- Stack
- Memory
- Breakpoints
- Backtrace

Voltron is built on a JSON/HTTP API which is available over TCP and UNIX domain sockets, and can be used to build custom UI views.

It looks something like this with LLDB:

![voltron example LLDB](http://i.imgur.com/p3XcagJ.png)

And this with GDB:

![voltron example GDB](http://i.imgur.com/JHq1zgG.png)


Support
-------

`voltron` is built primarily for LLDB. GDB and VDB are also supported to some extent.

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

    This part can go in your `.lldbinit` or `.gdbinit` so it's automatically executed when the debugger starts.

    Intel is the only disassembly flavour currently supported for syntax highlighting.

2. Start your debugger. On LLDB you need to call `voltron init` after you load the inferior, as a target must be loaded before Voltron's hooks can be installed. This means `voltron init` cannot be called from `.lldbinit` the way it can from `.gdbinit`. Hopefully this will be remedied with a more versatile hooking mechanism in a future version of LLDB (this has been discussed with the developers).

        $ lldb file_to_debug
        (lldb) voltron init

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view register
        $ voltron view stack
        $ voltron view disassembly
        $ voltron view backtrace
        $ voltron view command 'reg read'

4. Set a breakpoint and run your inferior. Once the inferior has started and the debugger has stopped (either because you interrupted it or because it hit a breakpoint) the views will update.

        (*db) b main
        (*db) run

5. The debugger should hit the breakpoint and the views will be updated. A forced update can be triggered with the following command:

        (lldb) voltron stopped

Documentation
-------------

See the [wiki](https://github.com/snare/voltron/wiki) on github.

Bugs
----

There are some known issues with GDB.

GDB on some distros is built with Python 3, but the system's Python is version 2. If Voltron is installed into Python 2's `site-packages` it will not work with GDB. See [this page on the wiki](https://github.com/snare/voltron/wiki/Voltron-on-Ubuntu-14.04-with-GDB) for installation instructions.

There is no clean way to hook GDB's exit, only the inferior's exit, so the Voltron server is started and stopped along with the inferior. This results in views showing "Connection refused" before the inferior has been started.

Due to a limitation in the GDB API, the views are only updated each time the debugger is stopped (e.g. by hitting a breakpoint), so view contents are not populated immediately when the view is connected, only when the first breakpoint is hit.

If the stack view is causing GDB to hang then it must be launched **after** the debugger has been launched, the inferior started, and the debugger stopped (e.g. a breakpoint hit). This is due to a GDB bug that has not yet been resolved.

See the [issue tracker](https://github.com/snare/voltron/issues) on github.

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
