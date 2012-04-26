from nose.tools import eq_
from nucleon import tests
app = tests.get_test_app(__file__)


def teardown():
    pool = app.app.get_amqp_pool()
    pool.close()


def test_0_version():
    resp = app.get('/')
    eq_(resp.json, {'version': '0.0.1'})
