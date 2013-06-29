voltron
=======

A half-arsed UI module for GDB & LLDB. 
--------------------------------------

I got sick of GDB's (lack of) UI, so I built this. fG!'s [gdbinit](https://github.com/gdbinit/Gdbinit) makes GDB slightly more bearable, and this does a similar job in a different way. `voltron` allows you to attach views running in other terminal windows to a GDB session, resulting in a more modular and flexible UI like you get in a GUI debugger like WinDbg, Immunity Debugger, OllyDbg, etc. It's not in the same league as a proper GUI debugger, but it does make GDB more bearable.

I initially built this to work with GDB but with the idea that I'd add LLDB support at some point. That point is now! Voltron now works with LLDB as well.

It's basically held together by sticky tape, so don't expect too much.

[![voltron example](http://github.com/snarez/voltron/raw/master/example.png)](#example)

Requirements
------------

`voltron` only works with GDB version 7 and later as it uses the Python API. If you're using Apple's GDB v6 you're out of luck; however, there is a project in the works to port some of Apple's hacks to version 7, so keep an eye out for that.

`voltron` also supports LLDB's python API.

Usage
-----

1. Load `voltron` into your debugger (these could go in your `.gdbinit` or `.lldbinit`)

		source /path/to/voltron.py 						# for GDB
		command script import /path/to/voltron.py 		# for LLDB

2. Fire up the debugger and start the `voltron` server thread (you could also put this in your `.gdbinit`/`.lldbinit`)

		$ gdb whatever
		gdb$ voltron start

		$ lldb whatever
		(lldb) voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

		$ voltron.py reg -v
		$ voltron.py stack
		$ voltron.py disasm
		$ voltron.py bt
		$ voltron.py cmd 'x/32x $rip'	# GDB
		$ voltron.py cmd 'reg read' 	# LLDB

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated.

5. Before you exit the debugger, execute the following command or GDB will hang since the domain socket will still be open. LLDB seems to handle this OK.

		gdb$ voltron stop

Bugs
----

If you don't `voltron stop` before you try to exit GDB the domain socket remains open, and GDB will hang. I couldn't see a hook in the python API to get a notification when GDB is about to exit. It's probably there, but I'll fix it later. Maybe.

There are probably others.

Development
-----------

I hacked this together in a night and I don't have the motivation to do any further work on it at this stage, but I may add to it as I use it more.

Things I probably will do at some stage in the not too distant future:

* Better colour support throughout all views like in the register view
* Move a bunch of the colour and template stuff to a config file
* Do something better than use Pygments with the sucky GDB lexer

Feel free to add to it and send a pull request.

If you want to add a new view type you'll just need to add a new subclass of `VoltronView` (see the others for examples) that registers for updates and renders data for your own message type, and potentially add some code to `VoltronCommand`/`VoltronGDBCommand`/`VoltronLLDBCommand` to grab the necessary data and cram it into an update message.

License
-------

This software is released under the "Buy snare a beer" license. If you use this and don't hate it, buy me a beer at a conference some time.

FAQ
---

Q: Dude, why don't you just use X?

A: IDA's debugger doesn't work with Y, LLDB doesn't work with Z, none of the GDB UIs are any good for assembly-level debugging, and I don't use Windows.
