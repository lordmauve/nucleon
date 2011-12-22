import puka
from gevent.queue import Queue
from nucleon.amqp.connection import PukaConnection
from contextlib import contextmanager
from puka.exceptions import ConnectionBroken

import logging

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
        if not cls._instances.has_key(name):
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
        self.queue = Queue(size)

        for x in xrange(size):
            client = self._open_connection(amqp_url)
            self.queue.put(client)

    def _open_connection(self, amqp_url):
        """
        Opens an AMQP connection (internal API).

        Arguments

        :amqp_url: configuration string for puka library (i.e.: amqp://user:pass@host:port/vhost)

        Returns

        :puka.Client:

        """
        client = puka.Client(amqp_url)
        promise = client.connect()
        client.wait(promise)
        return client

    @contextmanager
    def connection(self, block=True, timeout=None):
        """
        Provides context manager that handles AMQP connection lifecycle.

        It is a recommended assessor for connection.

        >>> with app.get_amqp_pool().connection() as conn:
        ...    conn.basic_sync_publish(...)

        >>> with app.get_amqp_pool(type="listen").connection() as conn:
        ...    conn.basic_sync_get_and_ack(...)

        Additionally when Connection has been broken (ConenctionBroken exception) than it reinitializes the connection on exit.
        This will not help you with existing messages but we're avoiding pool leaking.

        Arguments

        :block: if True (default) will wait for available connection in the pool
        :timeout: timeout when waiting for connection

        Returns

        :PukaConnection or None:

        """
        conn = self.queue.get(block,timeout)
        wrapped_conn = PukaConnection(self, conn)
        try:
            yield wrapped_conn

        except ConnectionBroken as ex:
            log.error("Recovered from ConnectionBroken exception.")
            try:
                #let's try to kindly close the connection
                promise = conn.close()
                conn.wait(promise)
            except:
                pass
            conn = None
            wrapped_conn.conn = None #let's make sure that failed connection will be pulled back to queue by gc
            wrapped_conn.pool = None
            wrapped_conn = None

            #let's reinitialize connection
            conn = self._open_connection(amqp_url)
            wrapped_conn = PukaConnection(self, conn)
        finally:
            wrapped_conn._put_back()

    def get_conn(self, block=True, timeout=None):
        """
        Returns AMQP conenction.

        Pulls connection object from pool and returns it. Unreferenced connection will eventually return to the pool.
        Unless explicitly required please please refrain from usage
        Recommended accessor is DictEntryPool.connection()

        Arguments

        :block: if True (default) will wait for available connection in the pool
        :timeout: timeout when waiting for connection

        Returns

        :PukaConnection or None:

        """
        conn = self.queue.get(block,timeout)
        return PukaConnection(self, conn)

