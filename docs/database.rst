PostgreSQL Database Access
==========================

Nucleon includes a wrapper for the psycopg2 PostgreSQL driver that shares a
pool of database connections between greenlets. The number of open database
connections is capped for performance.

Making database queries
-----------------------

A PostgreSQL connection pool can be retreived from each app's Application object.

.. class:: nucleon.framework.Application

    .. automethod:: get_database

        ``name`` is looked up in the application's config file, for the
        application's current environment. See :ref:`database-configuration`.

When a greenlet wishes to make a database request, it "borrows" a connection
from the pool. A context manager interface ensures that the connection is
returned to the pool when the greenlet no longer needs it.

.. automodule:: nucleon.database

.. autoclass:: nucleon.database.PostgresConnectionPool

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
