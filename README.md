Voltron
=======

Voltron is an extensible debugger UI for hackers. It allows you to attach utility views running in other terminals to your debugger (LLDB or GDB), displaying helpful information such as disassembly, stack contents, register values, etc, while still giving you the same debugger CLI you're used to. You can still have your pimped out custom prompt, macros, plugins, terminal colour scheme - whatever you're used to - but you get the added bonus of a sweet customisable heads-up display.

Voltron also provides a platform on which to build your own UI views, requesting and processing data from the debugger back end to suit your own requirements. To this end, Voltron provides (and uses internally) a JSON API available over UNIX domain sockets, TCP sockets and an HTTP server.

![voltron example](http://i.imgur.com/niDtVjN.png)

Support
-------

`voltron` is built primarily for LLDB. GDB version 7 and later and VDB are both supported.

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

A standard python setup script is included.

    # python setup.py install

This will install the `voltron` egg wherever that happens on your system, and an executable named `voltron` to `/usr/local/bin/`.

Quick Start
-----------

1. Configure your debugger to load Voltron when it starts by sourcing the `dbgentry.py` entry point script. The full path will be inside the `voltron` egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/dbgentry.py*.

    For LLDB:

        command script import /path/to/voltron/dbgentry.py

    For GDB:

        source /path/to/voltron/dbgentry.py
        voltron init

    This part can go in your `.lldbinit` or `.gdbinit` so it's automatically executed when the debugger starts.

2. Start your debugger. On LLDB you need to call `voltron init` after you load the inferior, as a target must be loaded before Voltron's hooks can be installed. This means `voltron init` cannot be called from `.lldbinit` the way it can from `.gdbinit`. Hopefully this will be remedied with a more versatile hooking mechanism in a future version of LLDB (this has been discussed with the developers).

        $ lldb file_to_debug
        (lldb) voltron init

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view register -v
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

See the [issue tracker](https://github.com/snare/voltron/issues) on github.

License
-------

This software is released under the "Buy snare a beer" license. If you use this and don't hate it, buy me a beer at a conference some time. This license also extends to other contributors - [richo](http://github.com/richo) definitely deserves a few beers for his contributions.

Credits
-------

Thanks to Azimuth Security for letting me spend time working on this.

Props to [richo](http://github.com/richo) for all his contributions to Voltron.

[fG!](http://github.com/gdbinit)'s gdbinit was the original inspiration for this project.

Thanks to [Willi](http://github.com/williballenthin) for implementing the VDB support.
