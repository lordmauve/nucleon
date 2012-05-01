"""Test connecting to databases defined in a config file.

For these tests to succeed, a PostgreSQL database must be running on port 5432
with accounts as defined in app.cfg.

"""

from nose.tools import eq_
from nucleon import tests
from nucleon.commands import syncdb, resetdb

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


def test_initialise_database():
    """Test the initdb command gives us a usable database."""
    pgpool = app.app.get_database('database')
    with pgpool.cursor() as c:
        c.execute('DROP TABLE IF EXISTS test CASCADE;')

    syncdb()
    with pgpool.cursor() as c:
        c.execute('SELECT name from test;')
        results = [r[0] for r in c.fetchall()]
        eq_(results, ['foo;', 'bar;', 'baz\'', ''])


def test_reinitialise_database():
    """Test that the initdb command restores the database completely."""
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
       of it's dependencies completely"""
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

