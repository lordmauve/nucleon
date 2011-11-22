from nose.tools import *
from nucleon.tests import get_test_app
import logging
import gevent
log = logging.getLogger(__name__)
app = get_test_app(__file__)


# Write your Nose tests below



def test_0_version():
    resp = app.get('/')
    eq_(resp.json, {'version': '0.0.1'})
