from __future__ import print_function

import logging
import logging.config
from collections import defaultdict

from .comms import *

DISASM_MAX = 32
STACK_MAX = 64

log = configure_logging()

class VoltronCommand (object):
    running = False

    # Methods for handling commands from the debugger
    def handle_command(self, command):
        global log
        if "start" in command:
            self.start()
        elif "stop" in command:
            self.stop()
        elif "status" in command:
            self.status()
        elif "update" in command:
            self.update()
        elif 'debug' in command:
            if 'enable' in command:
                log.setLevel(logging.DEBUG)
                print("Debug logging enabled")
            elif 'disable' in command:
                log.setLevel(logging.INFO)
                print("Debug logging disabled")
            else:
                print("Debug logging is currently " + ("enabled" if log.getEffectiveLevel() == logging.DEBUG else "disabled"))
        else:
            print("Usage: voltron <start|stop|update|status|debug>")

    def start(self):
        if not self.running:
            print("Starting voltron")
            self.running = True
            self.register_hooks()
        else:
            print("Already running")

    def stop(self):
        if self.running:
            print("Stopping voltron")
            self.unregister_hooks()
            self.stop_server()
            self.running = False
        else:
            print("Not running")

    def start_server(self):
        if self.server == None:
            self.server = Server()
            self.server.start()
        else:
            log.debug("Server thread is already running")

    def stop_server(self):
        if self.server != None:
            self.server.stop()
            self.server = None
        else:
            log.debug("Server thread is not running")

    def status(self):
        if self.running:
            print("There are {} clients attached".format(len(clients)))
            for client in clients:
                print("{} registered with config: {}".format(client, str(client.registration['config'])))
        else:
            print("Not running")

    def update(self):
        log.debug("Updating clients")

        # Make sure we have a target
        if not self.base_helper.has_target():
            return

        # Make sure we have a server and helper running
        if self.server == None:
            self.start_server()
        if self.helper == None:
            self.helper = self.base_helper.helper()

        # Process updates for registered clients
        log.debug("Processing updates")
        for client in filter(lambda c: c.registration['config']['update_on'] == 'stop', clients):
            event = {'msg_type': 'update', 'arch': self.helper.arch_group}
            if client.registration['config']['type'] == 'cmd':
                event['data'] = self.helper.get_cmd_output(client.registration['config']['cmd'])
            elif client.registration['config']['type'] == 'register':
                event['data'] = {'regs': self.helper.get_registers(), 'inst': self.helper.get_next_instruction()}
            elif client.registration['config']['type'] == 'disasm':
                event['data'] = self.helper.get_disasm()
            elif client.registration['config']['type'] == 'stack':
                event['data'] = {'data': self.helper.get_stack(), 'sp': self.helper.get_sp()}
            elif client.registration['config']['type'] == 'bt':
                event['data'] = self.helper.get_backtrace()

            # Add the new event to the queue
            self.server.enqueue_event(client, event)

    # These methods are overridden by the debugger-specific classes
    def register_hooks(self):
        pass

    def unregister_hooks(self):
        pass



class DebuggerHelper (object):
    # General methods for retrieving common types of registers
    def get_pc_name(self):
        return self.pc

    def get_pc(self):
        return self.get_register(self.pc)

    def get_sp_name(self):
        return self.sp

    def get_sp(self):
        return self.get_register(self.sp)


