from __future__ import print_function

import logging

from comms import *

DISASM_MAX = 32
STACK_MAX = 64

log = logging.getLogger('voltron')

class VoltronCommand (object):
    running = False

    def handle_command(self, command):
        global log
        if "start" in command:
            if 'debug' in command:
                log.setLevel(logging.DEBUG)
            self.start()
        elif "stop" in command:
            self.stop()
        elif "status" in command:
            self.status()
        elif "update" in command:
            self.update()
        else:
            print("Usage: voltron <start|stop|update|status>")

    def start(self):
        if not self.running:
            print("Starting voltron")
            self.running = True
            self.register_hooks()
            self.server = Server()
            self.server.start()
        else:
            print("Already running")

    def stop(self):
        if self.running:
            print("Stopping voltron")
            self.unregister_hooks()
            self.server.stop()
            self.server = None
            self.running = False
        else:
            print("Not running")

    def status(self):
        if self.running:
            print("There are {} clients attached".format(len(clients)))
            for client in clients:
                print("{} registered with config: {}".format(client, str(client.registration['config'])))
        else:
            print("Not running")

    def update(self):
        log.debug("Updating clients")
        arch = self.get_arch()

        for client in filter(lambda c: c.registration['config']['update_on'] == 'stop', clients):
            event = {'msg_type': 'update', 'arch': arch}

            if client.registration['config']['type'] == 'cmd':
                event['data'] = self.get_cmd_output(client.registration['config']['cmd'])
            elif client.registration['config']['type'] == 'register':
                event['data'] = {'regs': self.get_registers(), 'inst': self.get_next_instruction()}
            elif client.registration['config']['type'] == 'disasm':
                event['data'] = self.get_disasm()
            elif client.registration['config']['type'] == 'stack':
                event['data'] = {'data': self.get_stack(), 'sp': self.get_sp()}
            elif client.registration['config']['type'] == 'bt':
                event['data'] = self.get_backtrace()
                
            self.server.enqueue_event(client, event)

    def register_hooks(self):
        pass

    def unregister_hooks(self):
        pass

    def get_pc_name(self):
        arch = self.get_arch()
        if arch == 'x64':
            return 'rip'
        elif arch == 'x86':
            return 'eip'
        elif arch == 'arm':
            return 'pc'

    def get_pc(self):
        return self.get_register(self.get_pc_name())

    def get_sp_name(self):
        arch = self.get_arch()
        if arch == 'x64':
            return 'rsp'
        elif arch == 'x86':
            return 'esp'
        elif arch == 'arm':
            return 'sp'

    def get_sp(self):
        return self.get_register(self.get_sp_name())
