from gevent.event import AsyncResult


class WaitCounter(object):
    """
    A Counter with extras: wait_for_zero() which blocks until counter=0.
    Recommendation for a better name is more than welcome :)
    """

    def __init__(self):
        self.counter = 0
        self._wait_listeners = []

    def __str__(self):
        return '<%s counter=%s _wait_listeners[%s]>' % (self.__class__.__name__, self.counter, len(self._wait_listeners))

    def inc(self):
        self.counter += 1

    def wait_for_zero(self, timeout=None):
        """
        Waits for the counter to be zero
        """
        if self.counter == 0:
            return self.counter
        else:
            my_wait = AsyncResult()
            self._wait_listeners.append(my_wait)
            my_wait.get(timeout=timeout)
            try:
                self._wait_listeners.remove(my_wait)
            except ValueError:
                pass
            assert self.counter == 0, 'Shall be never interrupted'
            return self.counter

    def dec(self):
        assert self.counter > 0, 'Decrementing counter=%s, seems wrong to me' % self.counter
        self.counter -= 1
        if self.counter == 0:
            #notify listeners
            for listener in self._wait_listeners:
                listener.set()
            return True

    def __enter__(self):
        self.inc()
        return self

    def __exit__(self, typ, val, tb):
        self.dec()

