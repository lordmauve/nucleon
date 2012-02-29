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
