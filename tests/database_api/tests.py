import sys
import time
import thread
from cStringIO import StringIO
from nose.tools import eq_, raises, with_setup
from nucleon import tests
from nucleon.database import IntegrityError
from nucleon.database.api import NoResults, MultipleResults
import gevent
from gevent.pool import Group
from gevent.coros import Semaphore

app = tests.get_test_app(__file__)

from queries import (
    db, base_select, select_with_params, select_names,
    select_with_positional_params, simple_insert,
    do_insert, insert_with_id, slow_insert, retryable_transaction)


sqlscript = app.app.load_sql('database.sql')


def setup():
    pool = db.get_pool()
    reset = sqlscript.make_reinitialize_script(pool)
    out = StringIO()
    try:
        reset.execute(pool, out)
    except Exception:
        print out.getvalue()
        raise


def test_base_select():
    """Test selecting from a database."""
    eq_(base_select().rows, [
        {'id': 1, 'name': 'foo'},
        {'id': 2, 'name': 'bar'},
        {'id': 3, 'name': 'baz'},
    ])


def test_select_with_positional_params():
    """Test that parameters can be passed to a select."""
    eq_(select_with_positional_params(1, 'foo').rows, [
        {'id': 1, 'name': 'foo'},
    ])


def test_select_with_keyword_params():
    """Test that parameters can be passed to a select."""
    eq_(select_with_params(id=1, name='foo').rows, [
        {'id': 1, 'name': 'foo'},
    ])


@raises(TypeError)
def test_select_with_keyword_and_positional_params():
    """Test that selects reject mixed positional and keyword parameters"""
    select_with_params(1, name='foo').rows


@raises(TypeError)
def test_select_with_insufficient_keyword_params():
    """Test that required parameters are validated."""
    select_with_params(id='1').rows


@raises(TypeError)
def test_select_with_insufficient_positional_params():
    """Test that required parameters are validated."""
    select_with_params(1).rows


def test_select_column():
    """Test that it is possible to select a single column as a list"""
    eq_(select_names().flat, ['foo', 'bar', 'baz'])


@raises(TypeError)
def test_select_column_invalid():
    """Test that it is impossible to select multiple columns as a list"""
    base_select().flat


def test_select_unique():
    """Test that it is possible to select a single row as a dict"""
    eq_(select_with_params(id='1', name='foo').unique, {
        'id': 1,
        'name': 'foo',
    })


@raises(NoResults)
def test_select_unique_no_results():
    """Test that unique select raises an error if there are no results"""
    select_with_params(id='1', name='zap').unique


@raises(MultipleResults)
def test_select_unique_multiple_results():
    """Test that unique select raises an error if there are multiple results"""
    base_select().unique


@with_setup(setup)
def test_insert():
    """Test that we can execute transactions."""
    id = do_insert('asdf1')
    eq_(id, 4)
    assert select_with_params(id=id, name='asdf1').unique


@with_setup(setup)
def test_simple_insert():
    """Test that we can execute simple transactions."""
    id = simple_insert(name='asdf5').value
    eq_(id, 4)
    assert select_with_params(id=id, name='asdf5').unique


@with_setup(setup)
@raises(IntegrityError)
def test_transaction_conflict():
    """Test that transactions raise IntegrityError if they fail."""
    insert_with_id(7, 'asdf1')
    insert_with_id(7, 'asdf2')


@with_setup(setup)
def test_transactional():
    """Test that a transaction is atomic."""
    # Start a transaction in another thread that will block until we signal it
    sem = Semaphore(0)
    greenlet = gevent.spawn(slow_insert, sem)

    # Add something that will cause the transaction to fail
    with db.get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO test(id, name) VALUES(7, 'zonk')")
        conn.commit()

    # Let the transaction continue
    sem.release()

    # Wait for it to finish
    greenlet.join()

    # Check that the database does not contain the values from the transaction
    names = select_names().flat
    assert 'zonk' in names
    assert 'five' not in names
    assert 'seven' not in names


@with_setup(setup)
def test_transaction_retries():
    """Transactions can be retried if they fail."""
    g = Group()
    for i in range(4):
        g.apply_async(retryable_transaction)
    g.join()
    names = select_names().flat
    eq_(names[-4:], ['a3', 'a4', 'a5', 'a6'])


@with_setup(setup)
def test_auto_rollback():
    """Test that a transaction is rolled back if it fails."""
    # Start a transaction in another thread but kill it partway through
    sem = Semaphore(0)
    greenlet = gevent.spawn(slow_insert, sem)
    time.sleep(0.5)
    greenlet.kill(block=True)

    # Check that the database does not contain the values from the transaction
    names = select_names().flat
    assert 'five' not in names
    assert 'seven' not in names
