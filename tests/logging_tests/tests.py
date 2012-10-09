from nose.tools import eq_, with_setup
import os
import os.path
import urllib2
from time import sleep
import json
import time
import signal

from gevent.pool import Pool

current_dir = os.path.abspath(os.path.dirname(__file__))
pidfile = os.path.join(current_dir, 'nucleon.pid')
access_log = os.path.join(current_dir, 'access.log')
error_log = os.path.join(current_dir, 'error.log')
test_log = os.path.join(current_dir, 'test.log')


def kill_from_pidfile(pidfile):
    """Kill a process whose pid is in pidfile.

    Also waits for up to 10s for the process to stop, by polling /proc.
    """
    with open(pidfile, 'r') as pdfh:
        pid = pdfh.read().strip()

    print 'kill_from_pidfile: ', pid
    if pid and os.path.exists('/proc/%s' % pid):
        os.kill(int(pid), 15)

        for i in xrange(10):
            if not os.path.exists('/proc/%s' % pid):
                break
            sleep(1)
        else:
            os.killpg(int(pid), 9)


def setup():
    """Ensure pidfile does not exist. If it does, kill the process"""
    if os.path.exists(pidfile):
        kill_from_pidfile(pidfile)
        os.unlink(pidfile)
    if os.path.exists(error_log):
        os.unlink(error_log)
    if os.path.exists(access_log):
        os.unlink(access_log)
    if os.path.exists(test_log):
        os.unlink(test_log)


def teardown():
    """At the end of tests, try and kill nucleon and cleanup"""
    if os.path.exists(pidfile):
        # kill_from_pidfile(pidfile)

        # Ensure pidfile does not exist
        os.remove(pidfile)
        assert not os.path.exists(pidfile)

        # Lastly, test daemon is not running
#        if pid:
#            eq_(not os.path.exists('/proc/%s' % pid), True)


def wait_for_pidfile():
    """Waits for the pidfile to be created for a maximum of 10 secs"""
    total_wait = 0
    poll_freq = 0.5
    while True:
        sleep(poll_freq)
        total_wait += poll_freq
        assert total_wait < 10, "pidfile (%s) wasn't written after 10s" % pidfile
        try:
            with open(pidfile, 'r') as f:
                pid = f.read().strip()
                if pid:
                    return pid
        except (IOError, OSError):
            continue


def start_server(port=7001):
    """Spawn the server on the given port, and wait for it to come up."""
    print 'Test: starting nucleon server'
    os.system("nucleon start --port=%d --pidfile=%s --access_log=%s --error_log=%s"
            % (port, pidfile, access_log, error_log))
    wait_for_pidfile()
    sleep(2)  # Wait for the app to become ready


def stop_server():
    pid = open(pidfile).read()
    print 'Test: stopping nucleon server, pid:', pid
    os.system('kill -INT %s' % pid)
    sleep(2)


@with_setup(setup, teardown)
def test_logging():
    """Test that multiple processes are logging correctly.

    We query a specially crafted view that busy-waits to ensure requests are
    load-balanced between all listening workers; the response contains process
    details of the worker that served it.

    """
    results = {
        'pgrps': set(),
        'pids': set(),
        'failures': 0,
    }

    start_server(port=7005)

    def get_stat():
        try:
            resp = urllib2.urlopen('http://localhost:7005/')
            r = json.load(resp)
        except Exception, e:
            print 'exc: ', e
            results['failures'] += 1
        else:
            results['pgrps'].add(r['pgrp'])
            results['pids'].add(r['pid'])

    pool = Pool(size=10)
    for i in xrange(1000):
        pool.spawn(get_stat)

    pool.join(timeout=20, raise_error=True)

    eq_(results['failures'], 0)
    assert len(results['pids']) > 1
    eq_(len(results['pgrps']), 1)

    stop_server()
    # Check that access log was written correctly
    for line in open(access_log, 'r'):
        assert len(line.split()) == 11, 'Invalid access_log line: %s' % line
