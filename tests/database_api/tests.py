import sys
from cStringIO import StringIO
from nose.tools import eq_, raises
from nucleon import tests
from nucleon.database.api import NoResults, MultipleResults
app = tests.get_test_app(__file__)

from queries import (
    db, base_select, select_with_params, select_names,
    select_with_positional_params)


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
