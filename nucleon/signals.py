import gevent.pool


class Signal(object):
    """A basic signal dispatch class.

    Each signal represents a single type of event to which callbacks can be
    registered.

    When fired, all the callbacks are executed, either in turn or concurrently
    using greenlets.
    """
    def __init__(self):
        self.callbacks = {}

    def connect(self, callback, dispatch_uid=None):
        """Register a new callback to be called when the signal is fired.

        If given, dispatch_uid is a unique identifier for the callback
        registration. If the same dispatch_uid is given again the latter
        callback will replace the existing one.
        """
        self.callbacks[dispatch_uid or id(callback)] = callback
        return callback

    __call__ = connect

    def disconnect(self, callback=None, dispatch_uid=None):
        """Remove a previously registered callback.

        Either callback or dispatch_uid must be given. KeyError is thrown if
        the callback is not registered.

        """
        if dispatch_uid:
            del(self.callbacks[dispatch_uid])
        elif callback:
            del(self.callbacks[id(callback)])
        else:
            raise ValueError("You must pass a callback or dispatch_uid to " +
                "Signal.disconnect()")

    def fire(self, *args, **kwargs):
        """Fire the signal.

        The positional arguments args and keyword arguments kwargs are passed
        to each callback.

        This runs all of the callbacks one after the other, in the current
        greenlet.
        """
        for callback in self.callbacks.values():
            callback(*args, **kwargs)

    def fire_async(self, args=(), kwargs={}, concurrency=None):
        """Fire the signal asynchronously - each callback in its own greenlet.

        If concurrency is given, it is the limit on the number of dispatching
        greenlets to execute concurrently.
        """
        pool = gevent.pool.Pool(size=concurrency)
        for callback in self.callback.values():
            pool.apply_async(callback, args, kwargs)


# Fired when the application starts, before serving
on_initialise = Signal()

# Fired after the web service starts
on_start = Signal()
