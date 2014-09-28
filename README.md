voltron
=======

A half-arsed UI module for GDB & LLDB.
--------------------------------------

Voltron is an unobtrusive debugger UI for hackers. It allows you to attach utility views running in other terminals to your debugger, displaying helpful information such as disassembly, stack contents, register values, etc, while still giving you the same GDB or LLDB CLI you're used to. You can still have your pimped out custom prompt, macros, GDB and LLDB plugins, terminal colour scheme - whatever you're used to - but you get the added bonus of a sweet customisable heads-up display.

Voltron also provides a platform on which to build your own UI views, requesting and processing data from the debugger back end to suit your own requirements. To this end, Voltron provides (and uses internally) a JSON API available over UNIX domain sockets, TCP sockets and an HTTP server.

[![voltron example](http://ho.ax/voltron.png)](#example)

Support
-------

`voltron` supports GDB version 7 and later, and recent LLDB versions.

The following architectures are supported:
* x86
* x86_64
* armv7s
* arm64

arm64 support is LLDB-only at this stage.

Installation
------------

A standard python setup script is included.

    # python setup.py install

This will install the `voltron` egg wherever that happens on your system, and an executable named `voltron` to `/usr/local/bin/`.

`voltron console` requires the `rl` Python module. Install it with:

    $ pip install rl

Quick Start - GDB
-----------------

1. Add `voltron` to your `.gdbinit`. The full path will be inside the `voltron` egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/dbgentry.py*. Add the following lines to your `.gdbinit` to load voltron and install its hooks:

        source /path/to/voltron/dbgentry.py
        voltron start

2. Fire up the debugger:

        $ gdb file_to_debug

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view reg -v
        $ voltron view stack
        $ voltron view disasm
        $ voltron view bt
        $ voltron view cmd 'x/32x $rip'

4. Set a breakpoint and run your inferior. Once the inferior has started, the views will be able to connect, but they won't update until the debugger hits the first breakpoint.

        gdb$ b main
        gdb$ run

5. The debugger should hit the breakpoint and the `voltron` views will be updated. A forced update can be triggered with the following command:

        gdb$ voltron update

Quick Start - LLDB
------------------

1. Load `voltron` into your debugger (this could go in your `.lldbinit`). The full path will be inside the `voltron` egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/dbgentry.py*.

        command script import /path/to/voltron/dbgentry.py

2. Fire up the debugger and start the `voltron` server thread. Unfortunately, this cannot be done from `.lldbinit` as it can with `.gdbinit` as a target must be loaded before `voltron`'s hooks can be installed. Hopefully this will be remedied with a more versatile hooking mechanism in a future version of LLDB (this has been discussed with the developers).

        $ lldb file_to_debug
        (lldb) voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view reg -v
        $ voltron view stack
        $ voltron view disasm
        $ voltron view bt
        $ voltron view cmd 'reg read'

4. Set a breakpoint and run your inferior. Once the inferior has started, the views will be able to connect, but they won't update until the debugger hits the first breakpoint.

        (lldb) b main
        (lldb) run

5. The debugger should hit the breakpoint and the `voltron` views will be updated. A forced update can be triggered with the following command:

        (lldb) voltron update

Documentation
-------------

See the [wiki](https://github.com/snare/voltron/wiki) on github.

Bugs
----

See the [issue tracker](https://github.com/snare/voltron/issues) on github.

License
-------

This software is released under the "Buy snare a beer" license. If you use this and don't hate it, buy me a beer at a conference some time. This license also extends to other contributors - richo definitely deserves a few beers for his contributions.

Credits
-------

Thanks to Azimuth Security for letting me spend time working on this.

Props to [richo](http://github.com/richo) for all his contributions to Voltron.

[fG!](http://github.com/gdbinit)'s gdbinit was the original inspiration for this project.
