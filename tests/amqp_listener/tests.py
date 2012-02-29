from nose.tools import eq_
from nucleon import tests
app = tests.get_test_app(__file__)


def test_0_version():
    resp = app.get('/')
    eq_(resp.json, {'version': '0.0.1'})
