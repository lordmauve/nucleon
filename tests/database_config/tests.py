"""Test connecting to databases defined in a config file.

For these tests to succeed, a PostgreSQL database must be running on port 5432
with accounts as defined in app.cfg.

"""

from nose.tools import *
from nucleon.tests import get_test_app
app = get_test_app(__file__)


def test_config_string_without_port():
    """Test that if unspecified, we connect on the default PostgreSQL port."""
    pgpool = app.app.get_database()
    eq_(pgpool.settings['port'], 5432)


def test_secondary_database():
    """Test database connections with different configurations."""
    pgpool = app.app.get_database('database2')
    eq_(pgpool.settings['user'], 'some_other_user')
    eq_(pgpool.settings['port'], 5432)


def test_db_op():
    """Test that a database query works."""
    resp = app.get('/2')
    eq_(resp.json['x^2'], 4)


from nucleon.commands import syncdb, resetdb

def test_initialise_database():
    """Test the initdb command gives us a usable database."""
    syncdb()
    pgpool = app.app.get_database('database')
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
