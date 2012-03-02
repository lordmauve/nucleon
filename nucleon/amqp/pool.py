import puka
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
        self.next = 0

        for x in xrange(size):
            client = self._open_connection(amqp_url)
            wrapped_client = PukaConnection(self, client)
            self.pool.append(wrapped_client)

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

    def connection(self):
        """
        Get a connection from the connection pool.

        Returns

        :PukaConnection or None:

        """
        connection = self.pool[self.next]
        # round-robin
        if self.next == self.max_pool_size - 1:
            self.next = 0
        else:
            self.next += 1
        return connection
        # if self.queue.qsize() < 1:
        #     # if pool is empty create a new connection
        #     wrapped_conn = PukaConnection(self,
        #                     self._open_connection(self.amqp_url))
        #     print 'Puka pool empty. creating new connection. ', wrapped_conn.conn
        # else:
        #     wrapped_conn = self.queue.get(block, timeout)

        # try:
        #     yield wrapped_conn
        # except Exception as ex:
        #     print 'Connection broken exception raised: ', traceback.format_exc()
        #     try:
        #         #let's try to kindly close the connection
        #         promise = wrapped_conn.close()
        #     except:
        #         pass

        #     #let's reinitialize connection
        #     conn = self._open_connection(self.amqp_url)
        #     wrapped_conn = PukaConnection(self, conn)
        # finally:
        #     print 'pool: putting back connection ', wrapped_conn.conn
        #     self.put_back(wrapped_conn)


    # def put_back(self, connection):
    #     """
    #     Puts back a connection into the pool, if the max_queue_size is not reached.
    #     """
    #     if self.queue.qsize() < self.max_queue_size:
    #         self.queue.put(connection)
    #     else:
    #         print 'Queue full, so closing extra connection. ', connection.conn
    #         try:
    #             connection.close()
    #         except:
    #             pass

    # def get_conn(self, block=True, timeout=None):
    #     """
    #     Deprecated. Use the connection() context manager instead.

    #     Returns AMQP conenction.

    #     Pulls connection object from pool and returns it. Unreferenced connection will eventually return to the pool.
    #     Unless explicitly required please please refrain from usage
    #     Recommended accessor is DictEntryPool.connection()

    #     Arguments

    #     :block: if True (default) will wait for available connection in the pool
    #     :timeout: timeout when waiting for connection

    #     Returns

    #     :PukaConnection or None:

    #     """
    #     conn = self.queue.get(block,timeout)
    #     return conn
