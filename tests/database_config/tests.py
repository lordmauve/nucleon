"""Test connecting to databases defined in a config file.

For these tests to succeed, a PostgreSQL database must be running on port 5432
with accounts as defined in app.cfg.

"""

from nose.tools import eq_
from nucleon import tests
from nucleon.commands import syncdb, resetdb
from nucleon.database import PostgresConnectionPool, ConnectionFailed
from nucleon.database.pgpool import parse_database_url, make_safe_url

app = tests.get_test_app(__file__)


def test_config_string_without_port():
    """Test that if unspecified, we connect on the default PostgreSQL port."""
    pgpool = app.app.get_database()
    eq_(pgpool.settings['port'], 5432)


def test_secondary_database():
    """Test database connections with different configurations."""
    pgpool = app.app.get_database('database2')
    eq_(pgpool.settings['user'], 'nucleondb2')
    eq_(pgpool.settings['port'], 5432)


def test_db_op():
    """Test that a database query works."""
    resp = app.get('/2')
    eq_(resp.json['x^2'], 4)


def test_make_safe_url():
    """We can generate a URL that is safe to log/display."""
    u = 'postgres://dave:secret@dbhost.tld/mydb'
    params = parse_database_url(u)
    eq_(make_safe_url(params), 'postgres://dave@dbhost.tld/mydb')


def test_make_safe_url_with_port():
    """We can generate a URL that is safe to log/display."""
    u = 'postgres://dave:secret@dbhost.tld:5119/mydb'
    params = parse_database_url(u)
    eq_(make_safe_url(params), 'postgres://dave@dbhost.tld:5119/mydb')


def test_invalid_connection_settings():
    """Invalid connection settings cause an appropriate error to be raised."""
    invalid_db = 'postgres://asf:123131@localhost/banaoakj'
    try:
        PostgresConnectionPool.for_url(invalid_db)
    except ConnectionFailed as e:
        eq_(e.args[0], 'Failed to connect to postgres://asf@localhost/banaoakj')
        return
    except Exception as e:
        raise AssertionError("Exception raised was %r" % e)
    else:
        raise AssertionError("No exception raised on invalid connection")


def test_initialise_database():
    """Test the syncdb command gives us a usable database."""
    pgpool = app.app.get_database('database')
    with pgpool.cursor() as c:
        c.execute('DROP TABLE IF EXISTS test CASCADE;')

    syncdb()
    with pgpool.cursor() as c:
        c.execute('SELECT name from test;')
        results = [r[0] for r in c.fetchall()]
        eq_(results, ['foo;', 'bar;', 'baz\'', ''])


def test_reinitialise_database():
    """Test that the resetdb command restores the database completely."""
    syncdb()
    pgpool = app.app.get_database('database')
    with pgpool.connection() as conn:
        c = conn.cursor()
        c.execute('ALTER TABLE test RENAME COLUMN name TO title;')
        c.execute('INSERT INTO test(title) VALUES(%s)', ('banana',))
        conn.commit()

    resetdb()
    with pgpool.cursor() as c:
        c.execute('SELECT name from test;')
        results = [r[0] for r in c.fetchall()]
        eq_(results, ['foo;', 'bar;', 'baz\'', ''])


def test_reinitialise_database_with_dependencies():
    """Test that the resetdb command restores the database and all
       of its dependencies completely"""
    syncdb()
    pgpool = app.app.get_database('database')
    with pgpool.connection() as conn:
        c = conn.cursor()
        c.execute('ALTER TABLE test RENAME COLUMN name TO title;')
        retval = c.execute('INSERT INTO test(title) VALUES(%s) RETURNING id', ('banana',))
        c.execute('INSERT INTO test2(test_id) VALUES(%s)', (retval,))
        conn.commit()

    resetdb()
    with pgpool.cursor() as c:
        c.execute('SELECT * from test;')
        all = c.fetchall()
        ids = [r[0] for r in all]
        names = [r[1] for r in all]
        eq_(names, ['foo;', 'bar;', 'baz\'', ''])

        c.execute('SELECT * from test2;')
        all = c.fetchall()
        test2_ids = [r[0] for r in all]
        eq_(len(test2_ids), 1)
        eq_(ids[-1], test2_ids[0])


