import time
import os
import signal
import logging
import urllib2
import json
from multiprocessing import Process

import gevent
from nose.tools import eq_
from nucleon import tests
import nucleon.commands


log = logging.getLogger(__name__)
app = tests.get_test_app(__file__)

processes = []

#TODO: to see failed asserts on gevent spawned functions please run as
# $ nose:nosetests -v -s


class SubNucleon(object):
    """
    Abstraction over Nucleon http/amqp server to start, kill, join it.

    Considered base APIs:
    - Subprocess was also nice but it required to provide hardcoded path to
      nucleon.py
    - sys.fork was interfering with nosetests (forked process inherited all
      nose environment)
    - multiprocessing.Process just works
    """
    def __init__(self):
        def starter():
            nucleon_app = nucleon.commands.start()
            nucleon_app()
        self.sp = Process(target=starter)
        self.sp.start()

    def sigusr1(self):
        os.kill(self.sp.pid, signal.SIGUSR1)

    def join(self):
        return self.sp.join()

    def sigterm(self):
        self.sp.terminate()


def setUp():
    """
    Starts nucleon server
    """
    processes.append(SubNucleon())


def get_page():
    """
    gets page from local nucleon app

    verifies that page return takes 3s (hardcoded in app.py)
    """
    t_start = time.time()
    f = urllib2.urlopen('http://localhost:8888/')
    resp = f.read()
    f.close()
    eq_(json.loads(resp), {'version': '0.0.1'})
    t_end = time.time()
    t_delta = t_end - t_start
    assert t_delta >= 3
    assert t_delta <= 3.5


def get_page_503():
    """
    gets 503 page from local nucleon app

    verifies that page returns instantly and code=503
    """
    t_start = time.time()
    code = 200
    try:
        f = urllib2.urlopen('http://localhost:8888/')
        f.read()
        f.close()
    except urllib2.HTTPError as e:
        code = e.code
    t_end = time.time()
    t_delta = t_end - t_start
    assert t_delta <= 0.5
    eq_(code, 503)


def test_signal():
    """
    tests graceful exit when in middle of 2 requests

    this test requires gevent monkey patched nosetest
    gets two pages in separate threads
    sends SIGUSR1
    verifies that now 503 page is received
    verifies that subprocess closes within threshold
    """
    gevent.sleep(1)
    g1 = gevent.spawn(get_page)
    gevent.sleep(1)
    g2 = gevent.spawn(get_page)
    gevent.sleep(1)
    processes[0].sigusr1()
    gevent.sleep(0.1)
    g3 = gevent.spawn(get_page_503)

    # raise_error passes exceptions (failed asserts) from greenlets
    gevent.joinall([g1, g2, g3], raise_error=True)
    try:
        gevent.with_timeout(2, processes[0].join)
        timeout_exception = False
    except gevent.Timeout:
        timeout_exception = True

    assert timeout_exception == False, 'server was not killed'


def tearDown():
    """
    Kills sub process independently from test flow
    """
    try:
        processes[0].sigterm()
    except OSError:
        pass
