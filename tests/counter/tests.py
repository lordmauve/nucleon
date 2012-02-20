import time
from nose.tools import *
from nucleon.tests import get_test_app
app = get_test_app(__file__)

from nucleon.framework import WaitCounter
import gevent


class TimeException(Exception):
    pass


def test_context_api():
    """
    Verify WaitCounter context api

    Enters and leaves WaitCounter context
    waits for zero value on counter
    """
    with WaitCounter() as c:
        assert c.counter == 1
    assert c.wait_for_zero() == 0, 'shall be zero'


def test_single_thread_counter():
    """
    Verify WaitCounter on single thread leaving at 0

    increments and decrements WaitCounter couple of times (sequentially) leaving counter as 0
    waits for zero value on counter within 1 second = instantly
    """
    try:
        with gevent.Timeout(1, exception=TimeException):
            c = WaitCounter()
            c.inc()
            c.dec()
            c.inc()
            c.inc()
            c.dec()
            c.dec()
            assert c.wait_for_zero() == 0, 'shall be zero'
    except TimeException:
        assert False, 'took to long'

def test_single_thread_counter_with_wait():
    """
    Verify WaitCounter on single thread leaving at 1

    increments and decrements WaitCounter couple of times (sequentially) leaving counter as 1
    waits for zero value on counter - shall timeout
    """
    try:
        with gevent.Timeout(1, exception=TimeException):
            c = WaitCounter()
            c.inc()
            c.dec()
            c.inc()
            c.inc()
            c.dec()
            assert c.wait_for_zero() == 0, 'shall be zero'
            assert False, 'took too short'
    except TimeException:
        return

def test_multi_thread_counter():
    """
    Verify WaitCounter usage in multithreaded environment

    spawns three threads where each of them does:
    - increment counter
    - wait number of seconds, decrements counter)

    expects to get wait_for_zero unlock in approx 1.3s
    """
    def long_usage(counter,seconds):
        counter.inc()
        gevent.sleep(seconds)
        counter.dec()


    c = WaitCounter()

    ts1 = time.time()

    gevent.spawn(long_usage,c,1)   # ends in 1 second from ts1
    gevent.sleep(0.3)
    gevent.spawn(long_usage,c,1)   # ends in 1.3 second from ts1
    gevent.sleep(0.3)
    gevent.spawn(long_usage,c,0.3) # ends in 0.9 second from ts1

    assert c.wait_for_zero() == 0, 'shall be zero'

    ts2 = time.time()
    delta = ts2-ts1
    assert delta <= 1.5, 'took too long'
    assert delta >= 1, 'took too short'

