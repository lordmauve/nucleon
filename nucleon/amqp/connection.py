import puka
import gevent
from gevent.coros import RLock
import logging

log = logging.getLogger(__name__)


def deprecated(func):
    log.info("WARNING: Function %s is deprecated." % func.__name__)
    return func

class PukaConnection(object):
    """
    Puka Connection proxy wrapper
    - on delete returns connection to the pool, although it's safer if it is managed by contextmanager
    - provides sync and async wrappers for common functions
    - assures connection reliability through locking
    - async is provided as Greenlets
    Don't initialize directly. Use nucleon.Application.get_amqp_pool()
    """

    def __init__(self, pool, conn):
        self.pool = pool
        self.conn = conn
        self.lock = RLock()

    def basic_sync_publish(self, *args, **kwargs):
        """
        blocking basic_publish wrapper
        """
        with self.lock:
            promise = self.conn.basic_publish(*args,**kwargs)
        with self.lock:
            return self.conn.wait(promise)

    def basic_async_publish(self, callback=None, *args, **kwargs):
        """
        non blocking basic_publish wrapper for fire and forget
        """
        gevent.spawn(self.basic_sync_publish, *args, callback=callback, **kwargs)

    def basic_sync_get_and_ack(self, *args, **kwargs):
        """
        blocking basic_get + basic_ack wrapper
        """
        with self.lock:
            promise = self.conn.basic_get(*args,**kwargs)
        with self.lock:
            resp = self.conn.wait(promise)
            self.conn.basic_ack(resp)
        return resp

    def basic_async_get_and_ack(self, callback=None, *args, **kwargs):
        """
        non blocking basic_get + basic_ack wrapper - async call
        """
        gevent.spawn(self.basic_sync_get_and_ack, *args, callback=callback, **kwargs)

    def __getattr__(self, item):
        """
        lock wrapper for raw connection
        """
        with self.lock:
            return getattr(self.conn,item)

    def __getitem__(self, item):
        """
        lock wrapper for raw connection
        """
        with self.lock:
            return self.conn[item]

    def _put_back(self):
        """
        returns connection to a pool
        """
        self.pool.queue.put(self.conn)
        self.conn = None
        self.pool = None

    def __del__(self):
        if self.conn:
            self._put_back()
