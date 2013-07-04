#
# voltron.gdb
#
# This is a set of utility commands for communicating with a voltron standalone server from
# plain old GDB macro commands. This is used to add some support for voltron to GDB version 6.
#

set $VOLTRON_STACK_SIZE = 256

set $voltron_running = 0

define voltron_dump_registers_x64
    dump value /tmp/voltron.reg.rip $rip
    dump value /tmp/voltron.reg.rax $rax
    dump value /tmp/voltron.reg.rbx $rbx
    dump value /tmp/voltron.reg.rbp $rbp
    dump value /tmp/voltron.reg.rsp $rsp
    dump value /tmp/voltron.reg.rdi $rdi
    dump value /tmp/voltron.reg.rsi $rsi
    dump value /tmp/voltron.reg.rdx $rdx
    dump value /tmp/voltron.reg.rcx $rcx
    dump value /tmp/voltron.reg.r8  $r8
    dump value /tmp/voltron.reg.r9  $r9
    dump value /tmp/voltron.reg.r10 $r10
    dump value /tmp/voltron.reg.r11 $r11
    dump value /tmp/voltron.reg.r12 $r12
    dump value /tmp/voltron.reg.r13 $r13
    dump value /tmp/voltron.reg.r14 $r14
    dump value /tmp/voltron.reg.r15 $r15
    dump value /tmp/voltron.reg.cs  $cs
    dump value /tmp/voltron.reg.ds  $ds
    dump value /tmp/voltron.reg.es  $es
    dump value /tmp/voltron.reg.fs  $fs
    dump value /tmp/voltron.reg.gs  $gs
    dump value /tmp/voltron.reg.ss  $ss
    dump value /tmp/voltron.reg.eflags $eflags
end

define voltron_update_registers
    voltron_dump_registers_x64
    shell ~/.gdb/voltron/voltron.py gdb6proxy reg
    shell rm /tmp/voltron.reg.*
end

define voltron_update_stack
    dump memory /tmp/voltron.stack $rsp ($rsp+$VOLTRON_STACK_SIZE)
    dump value /tmp/voltron.reg.rsp $rsp
    shell ~/.gdb/voltron/voltron.py gdb6proxy stack
    shell rm /tmp/voltron.stack
end

define voltron_start
    if $voltron_running == 0
        shell ~/.gdb/voltron/voltron.py server & ; echo $! >/tmp/voltron.pid
        set $voltron_running = 1
    else
        echo Already running\n
    end
end
document voltron_start
Start the voltron server.
end

define voltron_stop
    if $voltron_running == 1
        shell kill `cat /tmp/voltron.pid`
        shell rm /tmp/voltron.pid
        set $voltron_running = 0
    else
        echo Not running\n
    end
end
document voltron_stop
Stop the voltron server.
end

define voltron_status
    if $voltron_running == 1
        echo Voltron is running\n
    else
        echo Voltron is not running\n
    end
end
document voltron_status
Get the status of the voltron server.
end

define voltron_update
    voltron_update_registers
    voltron_update_stack
end
document voltron_update
Send an update to the voltron server.
end

# If you have your own hook-stop defined, comment this out and add `voltron_update` to yours
define hook-stop
    voltron_update
end