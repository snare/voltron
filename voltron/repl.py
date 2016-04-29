from .core import Client


class REPLClient(Client):
    """
    A Voltron client for use in the Python REPL (e.g. Calculon).
    """
    def __getattr__(self, key):
        try:
            res = self.perform_request('registers', registers=[key])
            if res.is_success:
                return res.registers[key]
            else:
                print("Error getting register: {}".format(res.message))
        except Exception as e:
            print("Exception getting register: {}".format(repr(e)))

    def __getitem__(self, key):
        try:
            d = {}
            if isinstance(key, slice):
                d['address'] = key.start
                d['length'] = key.stop - key.start
            else:
                d['address'] = key
                d['length'] = 1

            res = self.perform_request('memory', **d)

            if res.is_success:
                return res.memory
            else:
                print("Error reading memory: {}".format(res.message))
        except Exception as e:
            print("Exception reading memory: {}".format(repr(e)))

    def __call__(self, command):
        try:
            res = self.perform_request('command', command=command)
            if res.is_success:
                return res.output
            else:
                print("Error executing command: {}".format(res.message))
        except Exception as e:
            print("Exception executing command: {}".format(repr(e)))


V = REPLClient()
