from voltron.api import *
from voltron.plugin import *

def validate_target(func, *args, **kwargs):
    """
    A decorator that ensures that the specified target_id exists and
    is valid.

    Expects the target ID to be either the 'target_id' param in kwargs,
    or the first positional parameter.

    Raises a NoSuchTargetException if the target does not exist.
    """
    def inner(self, *args, **kwargs):
        # find the target param
        target_id = None
        if 'target_id' in kwargs and kwargs['target_id'] != None:
            target_id = kwargs['target_id']
        elif len(args):
            target_id = args[0]
        else:
            target_id = 0

        # if there was a target specified, check that it's valid
        if not self.target_is_valid(target_id):
            raise NoSuchTargetException()

        # call the function
        return func(self, *args, **kwargs)
    return inner

def validate_busy(func, *args, **kwargs):
    """
    A decorator that raises an exception if the specified target is busy.

    Expects the target ID to be either the 'target_id' param in kwargs,
    or the first positional parameter.

    Raises a TargetBusyException if the target does not exist.
    """
    def inner(self, *args, **kwargs):
        # find the target param
        target_id = None
        if 'target_id' in kwargs and kwargs['target_id'] != None:
            target_id = kwargs['target_id']
        elif len(args):
            target_id = args[0]
        else:
            target_id = 0

        # if there was a target specified, ensure it's not busy
        if self.target_is_busy(target_id):
            raise TargetBusyException()

        # call the function
        return func(self, *args, **kwargs)
    return inner

def lock_host(func, *args, **kwargs):
    """
    A decorator that acquires a lock before accessing the debugger to
    avoid API locking related errors with LLDB
    """
    def inner(self, *args, **kwargs):
        self.host_lock.acquire()
        try:
            res = func(self, *args, **kwargs)
            self.host_lock.release()
        except Exception, e:
            self.host_lock.release()
            raise e
        return res
    return inner



class DebuggerAdaptor(object):
    def target_exists(self, target_id=0):
        """
        Returns True or False indicating whether or not the specified
        target is present and valid.

        `target_id` is a target ID (or None for the first target)
        """
        try:
            target = self._target(target_id=target_id)
        except Exception, e:
            log.error("Exception checking if target exists: {} {}".format(type(e), e))
            return False
        return target != None

    def target_is_valid(self, target_id=0):
        """
        Returns True or False indicating whether or not the specified
        target is present and valid.

        `target_id` is a target ID (or None for the first target)
        """
        try:
            target = self._target(target_id=target_id)
        except:
            return False
        return target['state'] != "invalid"

    def target_is_busy(self, target_id=0):
        """
        Returns True or False indicating whether or not the specified
        target is busy.

        `target_id` is a target ID (or None for the first target)
        """
        try:
            target = self._target(target_id=target_id)
        except:
            raise NoSuchTargetException()
        return target['state'] == "running"