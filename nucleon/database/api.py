from functools import wraps

from ..config import settings
from .pgpool import PostgresConnectionPool
from . import IntegrityError


try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


class NoResults(Exception):
    """No results were returned, when one was expected."""


class MultipleResults(Exception):
    """Multiple results were returned, when one was expected."""


class Results(object):
    """A wrapper for database select results.

    Properties of this class allow coercion to various forms, if applicable."""

    def __init__(self, description, rows):
        self.description = description
        self._rows = rows

    def __iter__(self):
        """Iterate through results as dictionaries."""
        cols = tuple([col[0] for col in self.description])
        for r in self._rows:
            yield OrderedDict(zip(cols, r))

    @property
    def rows(self):
        """Return results as a list of dictionaries.

        The dictionaries returned are actually instances of OrderedDict, such
        that their iteration order matches the order of columns in the select
        query.

        """
        return list(self)

    @property
    def unique(self):
        """Return results as a single dictionary.

        This method is only applicable if the query returns a single row. If
        there are no rows, NoResults will be raised. If there are multiple
        rows, MultipleResults will be raised.

        """
        num_rows = len(self._rows)
        if num_rows == 0:
            raise NoResults()
        elif num_rows > 1:
            raise MultipleResults(num_rows)
        cols = [col[0] for col in self.description]
        return OrderedDict(zip(cols, self._rows[0]))

    @property
    def flat(self):
        """Return results as a list.

        This method is only applicable if the query selects a single column. If
        the results consist of more than one column, TypeError will be raised.

        """
        if len(self.description) != 1:
            msg = "Results set with %d cols cannot be treated as flat"
            raise TypeError(msg % len(self.description))
        return [r[0] for r in self._rows]

    @property
    def value(self):
        """Return a single value.

        This method is only applicable if the query selects a single column,
        and the results contain only a single row. If the results consist of
        more than one column, TypeError will be raised. If there are no rows,
        NoResults will be raised. If there are multiple rows, MultipleResults
        will be raised.
        """
        if len(self.description) != 1:
            msg = "Results set with %d cols cannot be treated as value"
            raise TypeError(msg % len(self.description))
        num_rows = len(self._rows)
        if num_rows == 0:
            raise NoResults()
        elif num_rows > 1:
            raise MultipleResults(num_rows)
        return self._rows[0][0]


def easy_query(func, query, *args, **kwargs):
    """Call func(query, p) where p is either `args` or `kwargs`.

    Positional arguments are converted to a tuple, keyword arguments are
    converted to a dict.

    If the argument spec is wrong, or both positional and keyword arguments are
    passed then this will raise a TypeError.

    """
    if args and kwargs:
        msg = "query cannot be called with both args and kwargs"
        raise TypeError(msg)

    if args:
        try:
            return func(query, args)
        except IndexError:
            raise TypeError("Invalid number of arguments")
    else:
        try:
            return func(query, kwargs)
        except KeyError:
            raise TypeError("Incorrect arguments")


class Transaction(object):
    """A wrapper for a single query/transaction.

    This allows the query to be called as a method, passing parameters. If
    multiple queries are specified (eg. separated by semicolons), all of those
    queries will be performed as a single transaction (ie. atomically).

    """
    def __init__(self, database, query):
        self.database = database
        self.query = query

    def __call__(self, *args, **kwargs):
        """Execute the query."""
        return easy_query(self.database.query, self.query, *args, **kwargs)


class ConnectionProxy(object):
    """Adapter for a psycopg2 connection to return Results."""

    def __init__(self, conn):
        self._conn = conn

    def query(self, query, *args, **kwargs):
        """Make a query on the connection and return a Results object."""
        c = self._conn.cursor()
        easy_query(c.execute, query, *args, **kwargs)
        if c.description is None:
            return c.rowcount
        return Results(c.description, c.fetchall())

    __call__ = query


class Database(object):
    """A database wrapper."""
    def __init__(self, name):
        """Create a database wrapper a the database named in settings.

        The connection setting will be looked up when the application
        is started; this means that the API is purely delarative when
        it is imported.
        """
        self.name = name

    def get_pool(self):
        """Get the connection pool for this database.

        Each Database instance maintains a single connection pool. This will be
        created and connections established if no pool has previously been
        connected.

        """
        try:
            return self._pool
        except AttributeError:
            db_url = getattr(settings, self.name)
            self._pool = PostgresConnectionPool.for_url(db_url)
            return self._pool

    def select(self, query):
        """Construct a transaction wrapper, alias for `make_query`."""
        return Transaction(self, query)

    def make_query(self, query):
        """Construct a transaction wrapper.

        A transaction wrapper behaves as a function where the arguments passed
        are parameters to the query.

        """
        return Transaction(self, query)

    def query(self, query, params=()):
        """Execute a query immediately, returning a Results object."""
        with self.get_pool().connection() as conn:
            c = conn.cursor()
            try:
                c.execute(query, params)
                conn.commit()
            except IntegrityError:
                conn.rollback()
                raise
            if c.description is None:
                return c.rowcount
            return Results(c.description, c.fetchall())

    def transaction(self, retries=0):
        """Decorator to make a function into a retryable transaction."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                attempts = 0
                with self.get_pool().connection() as conn:
                    proxy = ConnectionProxy(conn)
                    while True:
                        try:
                            retval = func(proxy, *args, **kwargs)
                            conn.commit()
                        except IntegrityError:
                            attempts += 1
                            if attempts > retries:
                                raise
                            conn.rollback()
                        except Exception:
                            conn.rollback()
                            raise
                        else:
                            return retval
            return wrapper
        return decorator
