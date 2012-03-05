from nose.tools import eq_
from nucleon import tests

from collections import Counter
from nucleon.signals import on_initialise, on_start, Signal


# Set up for initialised handler
initialised = False
started = False


@on_initialise
def set_initialised():
    global initialised
    initialised = True


@on_start
def set_started():
    global started
    started = True


# Trigger initialise/start handler
app = tests.get_test_app(__file__)


def test_on_initialise():
    """Test that the on_initialise signal fires when the TestApp is obtained"""
    assert initialised


def test_on_start():
    """Test that the on_start handler fires when the TestApp is obtained"""
    assert started


def test_signal_firing():
    """Test that signals dispatch to all callbacks."""
    s = Signal()
    output = set()

    s.connect(lambda x: output.add(x))
    s.connect(lambda x: output.add(not x))
    s.fire(True)

    eq_(output, set([True, False]))


def test_signal_unique_callback():
    """Test that the same callback cannot be re-registered"""
    s = Signal()
    output = []

    def handler(x):
        output.append(x)

    s.connect(handler)
    s.connect(handler)
    s.fire(True)

    eq_(output, [True])


def test_signal_unique_uid():
    """Test that callbacks cannot be re-registered if the uid is the same"""
    s = Signal()
    output = []

    s.connect(lambda x: output.append(x), dispatch_uid='uid')
    s.connect(lambda x: output.append(x), dispatch_uid='uid')
    s.fire(True)

    eq_(output, [True])


def test_signal_deregister_uid():
    """Test that callbacks can be deregistered by uid"""
    s = Signal()
    output = []

    s.connect(lambda x: output.append(x), dispatch_uid='pos')
    s.connect(lambda x: output.append(not x), dispatch_uid='neg')
    s.disconnect(dispatch_uid='pos')
    s.fire(True)

    eq_(output, [False])


def test_signal_deregister_reference():
    """Test that callbacks can be deregistered by reference"""
    s = Signal()
    output = Counter()

    def handler(x):
        output[x] += 1

    def handler2(x):
        output[not x] += 1

    s.connect(handler)
    s.connect(handler2)
    s.fire(True)
    s.disconnect(handler2)
    s.fire(True)
    s.disconnect(handler)
    s.fire(True)

    eq_(output, {True: 2, False: 1})
