import puka
import gevent
from gevent.lock import Semaphore
from gevent.event import Event
from gevent.queue import Queue
from nucleon.amqp.connection import PukaConnection
from contextlib import contextmanager
from puka.exceptions import ConnectionBroken

import logging
import traceback

log = logging.getLogger(__name__)


class PukaDictPool(object):
    """
    It's a dictionary storage for Puka pool singletons
    Use as:
    pool = PukaDictPool(name, size, amqp_url)

    """
    def __new__(cls, name, size, amqp_url, *args, **kwargs):
        """
        returns a pool of connections from dictionary entry for a specific configuration

        if not available than it initializes the pool and updates the dictionary
        """
        if not hasattr(cls, '_instances'):
            cls._instances = dict()
        if name not in cls._instances:
            cls._instances[name] = DictEntryPool(size, amqp_url, *args, **kwargs)
        return cls._instances[name]


class DictEntryPool(object):
    def __init__(self, size, amqp_url, *args, **kwargs):
        """
        Initializes a pool of pre-opened AMQP connections.

        Arguments

        :size: count of pre-opened connections
        :amqp_url: configuration string for puka library (i.e.: amqp://user:pass@host:port/vhost)

        """
        self.pool = []
        self.amqp_url = amqp_url
        self.max_pool_size = size

        # Control creation of connections
        self.sem = Semaphore(size)
        self.conn_ready = Event()

        self.next = -1

        # Open all connections, asynchronously for speed
        cs = []
        for i in xrange(self.max_pool_size):
            cs.append(gevent.spawn(self.connection))
        gevent.joinall(cs)

    def _open_connection(self):
        """Open an PukaConnection."""
        client = puka.Client(self.amqp_url)
        promise = client.connect()
        client.wait(promise)
        wrapped_client = PukaConnection(self, client)
        return wrapped_client

    def connection(self):
        """Get a connection from the connection pool."""
        if self.sem.acquire(blocking=False):
            conn = self._open_connection()
            self.pool.append(conn)
            self.conn_ready.set()
        else:
            self.conn_ready.wait()

        # round-robin
        self.next = (self.next + 1) % len(self.pool)
        return self.pool[self.next]

    def close(self):
        """Close all connections in the pool."""
        self.conn_ready.clear()
        conns = self.pool
        self.pool = []
        for conn in conns:
            conn.close()
            self.sem.release()
        self.next = 0
