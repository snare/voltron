function f_hex(number, pad)
{
    return ("000000000000000000000000000000" + number.toString(16)).substr(-pad).toUpperCase();
}

angular.module('VoltronApp.controllers', []).
controller('voltronController', function($scope, voltronAPIservice)
{
    $scope.version = null;
    $scope.registers = [];
    $scope.disassembly = null;
    var state = null;
    var new_regs = null;
    var old_regs = [];

    voltronAPIservice.version().success(function (response) {
        $scope.version = response.data;
    });

    var format_registers = function(new_regs, old_regs, arch) {
        fmt = []
        if (arch == 'x86_64') {
            regs = ['rip','rax','rbx','rcx','rdx','rbp','rsp','rdi','rsi','r8','r9','r10','r11','r12','r13','r14','r15']
            for (i = 0; i < regs.length; i++) {
                fmt.push({
                    name: (regs[i].length == 2 ? String.fromCharCode(160) + regs[i] : regs[i]),
                    value: f_hex(new_regs[regs[i]], 16),
                    class: (new_regs[regs[i]] != old_regs[regs[i]] ? "reg_highlight" : "reg_normal")
                })
            }
        }
        return fmt
    }

    var format_disasm = function(disasm) {
        lines = disasm.split();

        // trim lldb's "inferior`main:" so hljs works
        if (lines[0].indexOf("`") > -1) {
            lines.splice(0, 1);
        }

        return lines.join('\n');
    }

    var update = function() {
        // get target info
        voltronAPIservice.listTargets().success(function (response) {
            targets = response.data.targets;

            // make sure we have a target
            if (targets[0]['arch'] != null) {
                // update registers
                voltronAPIservice.readRegisters().success(function (response) {
                    // get new register values
                    new_regs = response.data.registers

                    // format registers
                    $scope.registers = format_registers(new_regs, old_regs, targets[0]['arch']);

                    // keep old registers
                    old_regs = new_regs;
                });

                // update disassembly
                voltronAPIservice.disassemble(null, 32).success(function (response) {
                    $scope.disassembly = response.data.formatted;
                });
            }
        });
    }

    var poll = function() {
        // wait for the next state change
        response = voltronAPIservice.wait(30).success(function (response) {
            if (response.status == "success") {
                update();
            }

            // wait for the next state change
            poll();
        });
    };

    // initial update
    update();

    // start waiting for debugger stops
    poll();
});