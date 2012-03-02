from nucleon import tests
from nose.tools import eq_
app = tests.get_test_app(__file__)


def test_version():
    resp = app.get('/')
    eq_(resp.json, {'version': '0.0.1'})


def test_path():
    resp = app.get('/path-based/foo')
    eq_(resp.json, {'path': 'foo'})


def test_404():
    resp = app.get('/some-nonexistent-path', status=404)
    assert resp.json['error'] == 'NOT_FOUND'


def test_dates_naive():
    """Test naive date and time serialization"""
    resp = app.get('/dates-naive')
    eq_(resp.json, {
        'datetime': '2012-02-21T11:57:11',
        'date': '2012-02-21',
        'time': '11:57:11'
    })


def test_dates_utc():
    """Test timezone-aware date and time serialization"""
    resp = app.get('/dates-utc')
    eq_(resp.json, {
        'datetime': '2012-02-21T11:57:11+00:00',
        'date': '2012-02-21',
        'time': '11:57:11+00:00'
    })


def test_dates_bst():
    """Test non-UTC timezone-aware date and time serialization"""
    resp = app.get('/dates-bst')
    eq_(resp.json, {
        'datetime': '2012-02-21T11:57:11+01:00',
        'date': '2012-02-21',
        'time': '11:57:11+01:00'
    })
