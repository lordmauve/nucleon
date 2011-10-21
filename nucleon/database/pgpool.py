import psycopg2

from contextlib import contextmanager
from gevent.coros import Semaphore
from gevent.queue import Queue, Empty


class PostgresConnectionPool(object):
    """A pool of psycopg2 connections shared between multiple greenlets."""

    def __init__(self, initial=1, limit=20, **settings):
        """Construct a pool of connections.

        settings are passed straight to psycopg2.connect. initial connections
        are opened immediately. More connections may be opened if they are
        required, but at most limit connections may be open at any one time.

        """
        self.settings = settings
        self.sem = Semaphore(limit)
        self.size = 0
        self.pool = []

        for i in xrange(initial):
            self.pool.append(self._connect())

    def _connect(self):
        """Connect to PostgreSQL using the stored connection settings."""
        pg = psycopg2.connect(**self.settings)
        self.size += 1
        print "PostgreSQL connection pool size:", self.size
        return pg

    @contextmanager
    def cursor(self):
        """Obtain a cursor from the pool. We reserve the connection exclusively
        for this cursor, as cursors are apparently not safe to be used in multiple
        greenlets.
        """
        with self.connection() as conn:
            yield conn.cursor()

    @contextmanager
    def connection(self):
        """Obtain a connection from the pool, as a context manager, so that the
        connection will eventually be returned to the pool.

        >>> pool = PostgresConnectionPool(**settings)
        >>> with pool.connection() as conn:
        ...     c = conn.cursor()
        ...     c.execute(...)
        ...     conn.commit()
        """
        self.sem.acquire()
        try:
            conn = self.pool.pop(0)
        except IndexError:
            conn = self._connect()

        try:
            yield conn
        except psycopg2.OperationalError:
            # Connection errors should result in the connection being removed
            # from the pool.
            #
            # Unfortunately OperationalError could possibly mean other things and
            # we don't know enough to determine which
            try:
                conn.close()
            finally:
                self.size -= 1
                conn = None
                raise
        except:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            if conn is not None:
                self.pool.append(conn)
            self.sem.release()

