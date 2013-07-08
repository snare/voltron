voltron
=======

A half-arsed UI module for GDB & LLDB. 
--------------------------------------

I got sick of GDB's (lack of) UI, so I built this. fG!'s [gdbinit](https://github.com/gdbinit/Gdbinit) makes GDB slightly more bearable, and this does a similar job in a different way. **voltron** allows you to attach views running in other terminal windows to a GDB session, resulting in a more modular and flexible UI like you get in a GUI debugger like WinDbg, Immunity Debugger, OllyDbg, etc. It's not in the same league as a proper GUI debugger, but it does make GDB more bearable.

I initially built this to work with GDB but with the idea that I'd add LLDB support at some point. That point is now! Voltron now works with LLDB as well.

It's basically held together by sticky tape, so don't expect too much.

[![voltron example](http://github.com/snarez/voltron/raw/master/example.png)](#example)

Requirements
------------

**voltron** supports GDB version 7, LLDB, and has limited support for GDB version 6.

1. Requires termcolor

		sudo easy_install termcolor

Configuration
-------------

A sample configuration file is included in the repo. Copy it to `~/.voltron` and mess with it and you should get the idea. Header and footer positions, visbility and colours are configurable along with other view-specific items (e.g. colours for labels and values in the register view).

In the example config at the top level, the "all_views" section sets up a base configuration to apply to all views. Each view can be configured individually overriding these settings. For example, the "stack_view" section in the example config overrides a number of these settings to reposition the title and info labels. The "register_view" section in the example config contains some settings overriding the default colours for the register view. Have a look at the source for other items in "FORMAT_DEFAULTS" that can be overridden in this section of the config.

Usage - GDBv7
-------------

1. Load **voltron** into your debugger (this could go in your `.gdbinit`)

		source /path/to/voltron.py

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.gdbinit`)

		$ gdb whatever
		gdb$ voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

		$ voltron.py reg -v
		$ voltron.py stack
		$ voltron.py disasm
		$ voltron.py bt
		$ voltron.py cmd 'x/32x $rip'

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

		gdb$ voltron update

5. Before you exit the debugger, execute the following command or GDB will hang since the domain socket will still be open.

		gdb$ voltron stop

Usage - GDBv6
-------------

**Note:** **voltron** only has limited support for GDBv6 as it's tough to get useful data out of GDB without the Python API. A set of GDB macros are included to interact with **voltron** (which in this case runs as a background process started by the `voltron_start` macro). Only the register and stack views are supported.

A `hook-stop` macro is included - if you have your own custom one (e.g. fG!'s) you should just add `voltron_update` to your own and comment out the one in `voltron.gdb`

1. Load the macros into your debugger (this could go in your `.gdbinit`)

		source /path/to/voltron.gdb

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.gdbinit`)

		$ gdb whatever
		gdb$ voltron_start

3. In another terminal (I use iTerm panes) start one of the UI views

		$ voltron.py reg -v
		$ voltron.py stack

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

		gdb$ voltron_update

5. Before you exit the debugger, execute the following command the server process will be left running in the background.

		gdb$ voltron_stop

Usage - LLDB
-------------

1. Load **voltron** into your debugger (this could go in your `.lldbinit`)

		command script import /path/to/voltron.py

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.lldbinit`)

		$ lldb whatever
		(lldb) voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

		$ voltron.py reg -v
		$ voltron.py stack
		$ voltron.py disasm
		$ voltron.py bt
		$ voltron.py cmd 'reg read'

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

		(lldb) voltron update

Bugs
----

If you don't `voltron stop` before you try to exit GDB the domain socket remains open, and GDB will hang. I couldn't see a hook in the python API to get a notification when GDB is about to exit. It's probably there, but I'll fix it later. Maybe.

There are probably others.

Development
-----------

I initially hacked this together in a night as a "do the bare minimum to make my life better" project, as larger projects of this nature that I start never get finished. A few people have expressed interest in it, so I've added a few bits and pieces to it and will probably continue to add to it occasionally.

Things I probably will do at some stage in the not too distant future:

* Better colour support throughout all views like in the register view
* Do something better than use Pygments with the sucky GDB lexer

Feel free to add to it and send a pull request.

If you want to add a new view type you'll just need to add a new subclass of `TerminalView` (see the others for examples) that registers for updates and renders data for your own message type, and potentially add some code to `VoltronCommand`/`VoltronGDBCommand`/`VoltronLLDBCommand` to grab the necessary data and cram it into an update message.

License
-------

This software is released under the "Buy snare a beer" license. If you use this and don't hate it, buy me a beer at a conference some time.

FAQ
---

Q: Dude, why don't you just use X?

A: IDA's debugger doesn't work with Y, LLDB doesn't work with Z, none of the GDB UIs are any good for assembly-level debugging, and I don't use Windows.
