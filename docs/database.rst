PostgreSQL Database Access
==========================

Nucleon includes a wrapper for the psycopg2 PostgreSQL driver that shares a
pool of database connections between greenlets. The number of open database
connections is capped for performance.

Making database queries
-----------------------

A PostgreSQL connection pool can be retreived from each app's Application object.

When a greenlet wishes to make a database request, it "borrows" a connection
from the pool. A context manager interface ensures that the connection is
returned to the pool when the greenlet no longer needs it.

.. automodule:: nucleon.database

.. autoclass:: nucleon.database.PostgresConnectionPool

    .. automethod:: for_name

    .. automethod:: for_url

        The required URL format is::

            postgres://username:password@host[:port]/database

        Note that username and password are not currently optional.

    .. automethod:: connection()

        A context manager that borrows a connection from the pool. The
        connection can be used exclusively within the wrapped section::

            with pgpool.connection() as conn:
                c = conn.cursor()
                c.execute('INSERT INTO fruit(name) VALUES(%s)', ('banana',))
                conn.commit()

        If there are no connections left in the pool, the requesting greenlet
        will block until a database connection is available.

    .. automethod:: cursor()

        A context manager that borrows a connection from the pool, using it to
        provide a single database cursor. This cursor can be used directly::

            with pgpool.cursor() as c:
                c.execute('SELECT * FROM fruit')
                return c.fetchall()

        This is exactly equivalent to ::

            with pgpool.connection() as conn:
                c = conn.cursor()
                ...

High-level API
--------------

A higher level API is available for pre-defining queries that can be executed
later. This is intended to save boilerplate and allow queries to be defined in
one place - by convention, a separate ``queries.py``.

The style of the API is largely declarative; queries can be declared in SQL
syntax but can be used as Python callables. For example, declaring and using a
query might work as follows::

    >>> db = Database('database')
    >>> get_customer = db.select("SELECT id, name FROM customers WHERE id=%s")
    >>> get_customer(52).unique
    {'id': 52, 'name': 'Leonard Winter'}

The entry point to this high-level API is the :py:class:`Database
<nucleon.database.api.Database>` class, which wraps a PostgreSQL connection
corresponding to a setting defined in the application :doc:`settings file
<configuration>`.

.. automodule:: nucleon.database.api

.. autoclass:: nucleon.database.api.Database
   :members:


When performing a query, the return value is an object that allows
transformation of the results into simple Pythonic forms.

.. autoclass:: nucleon.database.api.Results

    .. autoattribute:: rows

        Example::

            >>> db.query("SELECT id, name FROM customers").rows
            [{"id": 1, "name": u"Walter Forsyth"}, {"id": 2, "name": u"Simon Pye"}]

    .. autoattribute:: flat

        Example::

            >>> db.query("SELECT id FROM customers").flat
            [1, 2]

    .. autoattribute:: unique

        Example::

            >>> db.query("SELECT id, name FROM customers WHERE id=%s", 2).unique
            {"id": 2, "name": u"Simon Pye"}

    .. autoattribute:: value

        Example::

            >>> db.query("SELECT name FROM customers WHERE id=%s", 2).value
            u"Simon Pye"

A results instance is also iterable; iterating it is equivalent to iterating
``.rows``, except that it does not build a list of all results first.


Transaction Functions
---------------------

Sometimes we want to do more processing in Python than is possible using the
above approach - we may need to take results into Python code, operate on them,
and perform database actions as a result.

We can do this using a "transaction function" - effectively a block of code in
which database queries are either all committed or all rolled back. This is
written as a decorated function whose first position argument is a callable
that can be used to perform queries within the transaction context::

    db = Database('database')

    @db.transaction()
    def add_customer(q, name)
        return q('INSERT INTO customers(name) VALUES(%s)', name)

Additionally, it is possible to specify that such a transaction be
automatically retried a finite number of times - this is useful if there can be
integrity problems but the chances of such are relatively low.

For example, we can write a transaction to insert a record with the next
highest `id` value as follows (assume `id` has a uniqueness constraint)::

    @db.transaction(retries=3)
    def insert_value(q):
        lastid = q('SELECT max(id) FROM test').value
        return q(
            'insert into test(id, name) values(%s, %s)',
            lastid + 1, 'a%s' % lastid
        )

This would be retried up to three times (4 attempts total) if there was an
integrity error (ie. another client inserts the same id between the SELECT and
the INSERT.

