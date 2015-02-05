#!/usr/bin/env python
"""
Example Voltron client.

Start your debugger as follows:

$ lldb /tmp/inferior
Voltron loaded.
Run `voltron init` after you load a target.
(lldb) target create "/tmp/inferior"
Current executable set to '/tmp/inferior' (x86_64).
(lldb) voltron init
Registered stop-hook
(lldb) b main
Breakpoint 1: where = inferior`main, address = 0x0000000100000cf0
(lldb) run
Process 13185 launched: '/Volumes/Data/Users/snare/code/voltron/repo/tests/inferior' (x86_64)
Process 13185 stopped
* thread #1: tid = 0x1ee63, 0x0000000100000cf0 inferior`main, queue = 'com.apple.main-thread', stop reason = breakpoint 1.1
    frame #0: 0x0000000100000cf0 inferior`main
inferior`main:
-> 0x100000cf0:  push   rbp
   0x100000cf1:  mov    rbp, rsp
   0x100000cf4:  sub    rsp, 0x50
   0x100000cf8:  mov    dword ptr [rbp - 0x4], 0x0

Run this client in another terminal. Each time you `stepi` in the debugger,
the client will output the current RIP:

$ python client.py
Instruction pointer is: 0x100000CFF
Instruction pointer is: 0x100000D02
Instruction pointer is: 0x100000D06
Instruction pointer is: 0x100000D0D
Instruction pointer is: 0x100000D15
Instruction pointer is: 0x100000D1C
"""

import voltron
from voltron.core import Client


def main():
    # Create a client and connect to the server
    client = Client()
    client.connect()

    # Main event loop
    while True:
        # Wait for the debugger to stop again
        res = client.perform_request('wait')
        if res.is_success:
            # If nothing went wrong, get the instruction pointer and print it
            res = client.perform_request('registers', registers=['rip'])
            if res.is_success:
                print("Instruction pointer is: 0x{:X}".format(res.registers['rip']))
            else:
                print("Failed to get registers: {}".format(res))
        else:
            print("Error waiting for the debugger to stop: {}".format(res))
            break


if __name__ == "__main__":
    main()