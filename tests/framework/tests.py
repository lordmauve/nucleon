# coding: utf8
import sys
import re
import urllib
from nose.tools import eq_
from cStringIO import StringIO
from contextlib import contextmanager

from nucleon import tests
app = tests.get_test_app(__file__)


@contextmanager
def stderr(stream):
    """Context manager that replaces stderr while in a block."""
    stderr = sys.stderr
    sys.stderr = stream
    try:
        yield
    finally:
        stream.flush()
        sys.stderr = stderr


def test_failure():
    """Test that a failing call returns 500 and logs to stderr"""
    buf = StringIO()
    with stderr(buf):
        app.get('/', status=500)
    error_output = buf.getvalue()
    assert 'Traceback' in error_output, "Error output was %r" % error_output


UNICODE_CHARS = u'\u00a3\u20ac\u2603'  # pound, euro, snowman


def test_post_view():
    """Test that we can faithfully post Unicode strings as UTF-8"""
    request_headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }
    body = 'message=' + urllib.quote(UNICODE_CHARS.encode('utf8'))
    resp = app.post('/post', body,
        headers=request_headers)
    eq_(resp.json['message'], UNICODE_CHARS)


def test_post_view_defaults_to_utf8():
    """Test that we can faithfully post UTF8 without an explicit charset."""
    request_headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    body = 'message=' + urllib.quote(UNICODE_CHARS.encode('utf8'))
    resp = app.post('/post', body,
        headers=request_headers)
    eq_(resp.json['message'], UNICODE_CHARS)


def test_post_to_get_only_view():
    """Test that posting to a GET-only view yields a 405 response."""
    resp = app.post('/', status=405)
    eq_(resp.headers['Allow'], 'GET')
    eq_(resp.body, '')


def test_get_post_only_view():
    """Test that getting a POST-only view yields a 405 response."""
    resp = app.get('/post', status=405)
    allowed_methods = set(re.split(r',\s*', resp.headers['Allow']))
    eq_(allowed_methods, set(['POST', 'PUT']))
    eq_(resp.body, '')


# Tests for various response types


def test_404():
    """Test generating 404 responses with Http404"""
    resp = app.get('/404', status=404)
    eq_(resp.json, {
        'error': 'NOT_FOUND',
        'message': "This thing didn't exist"
    })


def test_400():
    """Test generating 400 responses with JsonErrorResponse"""
    resp = app.get('/400', status=400)
    eq_(resp.json, {
        'error': 'SOME_ERROR',
        'message': 'Some message'
    })
