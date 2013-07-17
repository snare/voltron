voltron
=======

A half-arsed UI module for GDB & LLDB. 
--------------------------------------

I got sick of GDB's (lack of) UI, so I built this. fG!'s [gdbinit](https://github.com/gdbinit/Gdbinit) makes GDB slightly more bearable, and this does a similar job in a different way. **voltron** allows you to attach views running in other terminal windows to a GDB or LLDB session, resulting in a more modular and flexible UI like you get in a GUI debugger like WinDbg, Immunity Debugger, OllyDbg, etc. It's not in the same league as a proper GUI debugger, but it does make GDB more bearable.

It's basically held together by sticky tape, so don't expect too much. I'm constantly developing this and pushing code out, so consider the `master` branch to be in flux and experimental at this stage.

[![voltron example](http://ho.ax/voltron.png)](#example)

I've taken a lot of inspiration from the way fG!'s `gdbinit` renders the registers, flags, jump info etc. So big thanks to him for all the hard work he's done on that over the years.

Support
-------

**voltron** supports GDB version 7, LLDB, and has limited support for GDB version 6.

The following architectures are supported:
* x86
* x86_64

Installation
------------

A standard python setup script is included.

    # python setup.py install

This will install the **voltron** egg wherever that happens on your system, and an executable named `voltron` to `/usr/local/bin/`.

You should also be able to use **voltron** without installing it by changing the paths used below to wherever you put the source. This won't work for the GDBv6 macros as it calls the `voltron` command without an absolute path, so you'll have to modify the macros if you don't want to install it and want to use it with GDBv6.

Configuration
-------------

A sample configuration file is included in the repo. Copy it to `~/.voltron` and mess with it and you should get the idea. Header and footer positions, visbility and colours are configurable along with other view-specific items (e.g. colours for labels and values in the register view).

In the example config at the top level, the "all_views" section sets up a base configuration to apply to all views. Each view can be configured individually overriding these settings. For example, the "stack_view" section in the example config overrides a number of these settings to reposition the title and info labels. The "register_view" section in the example config contains some settings overriding the default colours for the register view. Have a look at the source for other items in "format_defaults" that can be overridden in this section of the config.

There is also support for named view configurations for each type. The example configuration contains a config section called "some_named_stack_view", which is a modified version of the example stack view configuration. If you specify this name with the `-n` option, this named configuration will be added to the existing config for that view type:

        $ voltron stack -n "some_named_stack_view"

Some options specified in the configuration file can also be overridden by command line arguments. At this stage, just the show/hide header/footer options.

So the resulting order of precedence for configuration is:

1. defaults in source
2. "all_views" config
3. view-specific config
4. named view config
5. command line args

Each configuration level is added to the previous level, and only the options specified in this level override the previous level.

Help
----

**voltron** uses the `argparse` module with subcommands, so the command line interface should be relatively familiar. Top-level help, including a list of available subcommands, will be output with `-h`. Detailed help for subcommands can be obtained the same way:

    $ voltron -h
    $ voltron view -h
    $ voltron view reg -h

Usage - GDBv7
-------------

1. Load **voltron** into your debugger (this could go in your `.gdbinit`). The full path will be inside the **voltron** egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/voltron/gdbcmd.py*.

        source /path/to/voltron/gdbcmd.py

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.gdbinit`)

        $ gdb whatever
        gdb$ voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view reg -v
        $ voltron view stack
        $ voltron view disasm
        $ voltron view bt
        $ voltron view cmd 'x/32x $rip'

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

        gdb$ voltron update

5. Before you exit the debugger, execute the following command or GDB will hang since the domain socket will still be open.

        gdb$ voltron stop

Usage - GDBv6
-------------

**Note:** **voltron** only has limited support for GDBv6 as it's tough to get useful data out of GDB without the Python API. A set of GDB macros are included to interact with **voltron** (which in this case runs as a background process started by the `voltron_start` macro). Only the register and stack views are supported.

A `hook-stop` macro is included - if you have your own custom one (e.g. fG!'s) you should just add `voltron_update` to your own and comment out the one in `voltron.gdb`.

The macro file will be inside the **voltron** egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/voltron.gdb*.

1. Load the macros into your debugger (this could go in your `.gdbinit`)

        source /path/to/voltron.gdb

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.gdbinit`)

        $ gdb whatever
        gdb$ voltron_start

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view reg -v
        $ voltron view stack

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

        gdb$ voltron_update

5. Before you exit the debugger, execute the following command the server process will be left running in the background.

        gdb$ voltron_stop

Usage - LLDB
-------------

1. Load **voltron** into your debugger (this could go in your `.lldbinit`). The full path will be inside the **voltron** egg. For example, on OS X it might be */Library/Python/2.7/site-packages/voltron-0.1-py2.7.egg/voltron/lldbcmd.py*.

        command script import /path/to/voltron/lldbcmd.py

2. Fire up the debugger and start the **voltron** server thread (you could also put this in your `.lldbinit`)

        $ lldb whatever
        (lldb) voltron start

3. In another terminal (I use iTerm panes) start one of the UI views

        $ voltron view reg -v
        $ voltron view stack
        $ voltron view disasm
        $ voltron view bt
        $ voltron view cmd 'reg read'

4. The UI view code will attach to the server (via a domain socket) and refresh every time the debugger is stopped. So, set a break point and let the debugger hit it and everything should be updated. A forced update can be triggered with the following command: 

        (lldb) voltron update

Layout automation
-----------------

### tmux

There's a few tmux scripting tools around - [tmuxinator](https://github.com/aziz/tmuxinator) is one of them. You'll probably need to use the latest repo version (as of July 11, 2013) as the current stable version has a bug that results in narrow panes not being created properly or something. Seems to be resolved in the latest repo version.

Here's a sample **tmuxinator** config for a layout similar to the example screencap that works well on an 11" MacBook Air in fullscreen mode:

    project_name: voltron
    project_root: .
    cli_args: -v -2
    tabs:
      - madhax:
          layout: 15a8,169x41,0,0{147x41,0,0[147x13,0,0{81x13,0,0,60,65x13,82,0,61},147x19,0,14,62,147x7,0,34{89x7,0,34,63,57x7,90,34,64}],21x41,148,0,65}
          panes:
            - voltron view disasm
            - voltron view cmd "i b"
            - gdb
            - voltron view stack 
            - voltron view bt
            - voltron view reg

The `layout` option there configures the actual dimensions of the panes. You can generate the layout info like this:

    $ tmux list-windows
    1: madhax* (6 panes) [169x41] [layout 15a8,169x41,0,0{147x41,0,0[147x13,0,0{81x13,0,0,60,65x13,82,0,61},147x19,0,14,62,147x7,0,34{89x7,0,34,63,57x7,90,34,64}],21x41,148,0,65}] @11 (active)

Bugs
----

If you don't `voltron stop` before you try to exit GDB the domain socket remains open, and GDB will hang. I couldn't see a hook in the python API to get a notification when GDB is about to exit. It's probably there, but I'll fix it later. Maybe.

There are probably others.

Development
-----------

I initially hacked this together in a night as a "do the bare minimum to make my life better" project, as larger projects of this nature that I start never get finished. I'm continuing development on this in an ad hoc fashion. If you have a feature request feel free to add it as an issue on github, or add it yourself and send a pull request.

If you want to add a new view type you'll just need to add a new subclass of `TerminalView` (see the others for examples) that registers for updates and renders data for your own message type, and potentially add some code to `VoltronCommand`/`VoltronGDBCommand`/`VoltronLLDBCommand` to grab the necessary data and cram it into an update message.

License
-------

This software is released under the "Buy snare a beer" license. If you use this and don't hate it, buy me a beer at a conference some time.

FAQ
---

Q: Dude, why don't you just use X?

A: IDA's debugger doesn't work with Y, LLDB doesn't work with Z, none of the GDB UIs are any good for assembly-level debugging, and I don't use Windows.
