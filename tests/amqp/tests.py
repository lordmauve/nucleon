from nucleon.main import bootstrap_gevent
bootstrap_gevent()

from nose.tools import *
from nucleon import tests
from nucleon.config import settings
import logging
import gevent
from gevent.queue import Queue
from functools import wraps

#from nucleon.amqp.pool import PukaDictPool

log = logging.getLogger(__name__)
app = tests.get_test_app(__file__)


#can listeners share connection
#can senders share connection -> add lock

def amqp_setup():
    log.debug("setup")
    client = app.app.get_amqp_pool().connection()
    client.exchange_declare("unit_test_room")
    client.queue_declare(queue='listener1')
    client.queue_declare(queue='listener2')

    client.queue_bind(queue="listener1",
        exchange="unit_test_room", routing_key="user1")

    client.queue_bind(queue="listener2",
        exchange="unit_test_room", routing_key="user2")


def amqp_teardown():
    log.debug("tear_down")
    pool = app.app.get_amqp_pool()
    client = pool.connection()
    client.exchange_delete("unit_test_room")
    client.queue_delete(queue='listener1')
    client.queue_delete(queue='listener2')
#    pool.close()
#    PukaDictPool._instances = {}


def teardown():
    pool = app.app.get_amqp_pool()
    pool.close()


def with_timeout(seconds=5):
    """A decorator to automatically fail a test after `seconds` seconds."""
    def timeout_decorator(func):
        @wraps(func)
        def wrapper():
            exc = AssertionError("Test timed out (after %ss)" % seconds)
            timeout = gevent.Timeout(seconds, exception=exc)
            timeout.start()
            try:
                return func()
            finally:
                timeout.cancel()
        return wrapper
    return timeout_decorator

"""
Note message exchanges are registered at app.py

"""


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_02_connections():
    log.debug("test_02_connections")
    p1 = app.app.get_amqp_pool("publish")
    eq_(len(p1.pool), int(settings.amqp_publish_pool_size))
    p1 = app.app.get_amqp_pool("listen")
    eq_(len(p1.pool), int(settings.amqp_listen_pool_size))


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_05_get_publish_connection():
    log.debug("test_05_get_publish_connection")
    conn = app.app.get_amqp_pool().connection()
    log.debug("connection: %s" % conn)
    from nucleon.amqp.connection import PukaConnection
    assert isinstance(conn, PukaConnection)


def publish_message(conn, exchange, routing_key, body, callback=None):
    """
    Utility method to publish one message synchronously to given exchange
    """
    if callback:
        return conn.publish(exchange=exchange, routing_key=routing_key,
            body=body, callback=callback)
    else:
        return conn.publish(exchange=exchange, routing_key=routing_key,
            body=body)


def get_message(conn, queue, callback=None):
    """
    Utility method to get one message synchronously from given queue on given
    connection.
    """
    if callback:
        resp = conn.consume(queue=queue, callback=callback)
    else:
        resp = conn.consume(queue=queue)
    return resp




@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_sync_diff_connections():
    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_sync_diff_connections message 2'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    conn = app.app.get_amqp_pool().connection()
    # check that message was correctly published
    resp = get_message(conn, 'listener1')
    eq_(resp['body'], message_body)
    # acknowledge the message
    conn.ack(resp)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_sync_publish_consume():
    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_publish_sync message 1'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    # check that message was correctly published
    msg = get_message(conn, 'listener1')
    eq_(msg.body, message_body)
    # acknowledge the message
    msg.ack()


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_sync_multi_publish_consume():

    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume message 1'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    conn = app.app.get_amqp_pool().connection()
    # check that message was correctly published
    msg = get_message(conn, 'listener1')
    eq_(msg.body, message_body)
    # acknowledge the message
    msg.ack()

    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume message 2'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    conn = app.app.get_amqp_pool().connection()
    # check that message was correctly published
    msg = get_message(conn, 'listener1')
    eq_(msg.body, message_body)
    # acknowledge the message
    msg.ack()

    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume message 3'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    conn = app.app.get_amqp_pool().connection()
    # check that message was correctly published
    msg = get_message(conn, 'listener1')
    eq_(msg.body, message_body)
    # acknowledge the message
    msg.ack()


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_sync_multi_publish_consume_same_conn():

    conn = app.app.get_amqp_pool().connection()
    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume_same_conn message 1'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    # check that message was correctly published
    resp = get_message(conn, 'listener1')
    eq_(resp.body, message_body)
    # acknowledge the message
    conn.ack(resp)

    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume_same_conn message 2'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    # check that message was correctly published
    resp = get_message(conn, 'listener1')
    eq_(resp.body, message_body)
    # acknowledge the message
    conn.ack(resp)

    # publish a message to the exchange
    message_body = 'test_sync_multi_publish_consume_same_conn message 3'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)
    eq_(resp, {})

    # check that message was correctly published
    resp = get_message(conn, 'listener1')
    eq_(resp.body, message_body)
    # acknowledge the message
    conn.ack(resp)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_09_publish_sync_get_sync():
    """
    test_09_publish_sync_get_sync
    send message on connS1
    receive message on connR1

    send message on connS1
    receive message on connR2
    """
    log.debug("test_09_publish_get_sync")

    connS1 = app.app.get_amqp_pool().connection()
    connR1 = app.app.get_amqp_pool(type="listen").connection()
    connR2 = app.app.get_amqp_pool(type="listen").connection()
    log.debug("connection: %s" % connS1)
    log.debug("connection: %s" % connR1)
    log.debug("connection: %s" % connR2)
    from nucleon.amqp.pool import PukaConnection
    assert isinstance(connS1, PukaConnection)
    assert isinstance(connR1, PukaConnection)
    assert isinstance(connR2, PukaConnection)

    eq_(connS1.publish(exchange="unit_test_room",
            routing_key="user1", body="Hello my Get1"),
        {})

    resp = connR1.consume(queue="listener1")
    eq_(resp.body, "Hello my Get1")
    connR1.ack(resp)

    eq_(connS1.publish(exchange="unit_test_room",
            routing_key="user1", body="Hello my Get2"),
        {})
    resp = connR2.consume(queue="listener1")
    eq_(resp.body, "Hello my Get2")
    connR2.ack(resp)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_async_publish_consume():
    conn = app.app.get_amqp_pool().connection()
    message_body = 'test_async_publish_consume message 1'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)

    recv_queue = Queue()

    def recv_callback(msg):
        log.debug('test_async_publish_consume recv_callback called. result = %r', msg)
        recv_queue.put(msg)

    get_message(conn, 'listener1', callback=recv_callback)
    resp = recv_queue.get()
    eq_(resp.body, message_body)
    resp.ack()


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_async_multi_publish_consume():
    conn = app.app.get_amqp_pool().connection()
    # first message
    message_body = 'test_async_multi_publish_consume message 1'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)

    recv_queue = Queue()

    def recv_callback(msg):
        log.debug('test_async_multi_publish_consume recv_callback result = %r', msg)
        recv_queue.put(msg)

    get_message(conn, 'listener1', callback=recv_callback)
    resp = recv_queue.get()
    eq_(resp.body, message_body)
    conn.ack(resp)

    assert recv_queue.empty()

    # second message
    message_body = 'test_async_multi_publish_consume message 2'
    resp = publish_message(conn, 'unit_test_room', 'user1', message_body)

    resp = recv_queue.get()
    eq_(resp.body, message_body)
    conn.ack(resp)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(10)
def test_20_publish_async_get_async():
    """
    test_20_publish_async_get_async
    send message on connS1
    receive callback of send

    receive message on connR1
    receive callback of receive


    send message on connS1
    receive callback of send

    receive message on connR2
    receive callback of receive
    """
    log.debug("test_20_publish_async_get_async")
    connS1 = app.app.get_amqp_pool().connection()
    connR1 = app.app.get_amqp_pool(type="listen").connection()
    connR2 = app.app.get_amqp_pool(type="listen").connection()
    log.debug("connection: %s" % connS1)
    log.debug("connection: %s" % connR1)
    log.debug("connection: %s" % connR2)
    from nucleon.amqp.pool import PukaConnection
    assert isinstance(connS1, PukaConnection)
    assert isinstance(connR1, PukaConnection)
    assert isinstance(connR2, PukaConnection)

    sent_results = Queue()
    recv_results_r1 = Queue()
    recv_results_r2 = Queue()

    def sent_callback(promise, result):
        log.debug('sent_callback called')
        sent_results.put(result)
        log.debug("Received result %s" % result)

    def recv_callback_r1(result):
        log.debug('recv_callback_r1 called. result = %r', result)
        recv_results_r1.put(result)

    def recv_callback_r2(result):
        log.debug('recv_callback_r2 called. result = %r', result)
        recv_results_r2.put(result)

    message_body = 'HelloASync1'
    publish_message(connS1, 'unit_test_room', 'user1',
        message_body, callback=sent_callback)
    sent = sent_results.get()
    eq_(sent, {})

    promise1 = get_message(connR1, "listener1",
        callback=recv_callback_r1)
    msg = recv_results_r1.get()
    eq_(msg.body, message_body)
    msg.ack()
    connR1.cancel(promise1)

    message_body = 'HelloASync2'
    publish_message(connS1, 'unit_test_room', 'user1',
        message_body, callback=sent_callback)
    # connS1.publish(exchange = "unit_test_room",
    #     routing_key = "user1", body = "HelloASync2",
    #     callback=sent_callback)

    promise2 = get_message(connR2, "listener1",
        callback=recv_callback_r2)
    recv = recv_results_r2.get()
    eq_(recv.body, message_body)
    recv.ack()
    connR2.cancel(promise2)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_31_with_publish_get_async():
    log.debug("test_31_with_publish_get_async")

    connR = None
    sent_results = Queue()
    recv_results = Queue()

    def sent_callback(promise, result):
        sent_results.put(result)
        log.debug("Received result %s" % result)

    def recv_callback(result):
        log.debug('recv_callback called. result = %s', result)
        recv_results.put(result)

    conn = app.app.get_amqp_pool().connection()
    connR = app.app.get_amqp_pool(type="listen").connection()

    conn.publish(exchange="unit_test_room",
        routing_key="user1", body="WithHello1",
        callback=sent_callback)

    promise = connR.consume(queue="listener1",
        callback=recv_callback)

    recv = recv_results.get()
    sent = sent_results.get()
    eq_(sent, {})
    eq_(recv.body, "WithHello1")
    recv.ack()

    conn.publish(exchange="unit_test_room",
        routing_key="user1", body="WithHello1 again",
        callback=sent_callback)

    recv = recv_results.get()
    sent = sent_results.get()
    eq_(sent, {})
    eq_(recv.body, "WithHello1 again")
    recv.ack()
    connR.cancel(promise)

    assert sent_results.empty()
    assert recv_results.empty()

    conn = app.app.get_amqp_pool().connection()
    connR = app.app.get_amqp_pool(type="listen").connection()
    conn.publish(exchange="unit_test_room",
        routing_key="user1", body="WithHello2",
        callback=sent_callback)

    promise = connR.consume(queue="listener1",
        callback=recv_callback)

    recv = recv_results.get()
    sent = sent_results.get()
    eq_(sent, {})
    eq_(recv.body, "WithHello2")
    recv.ack()
    connR.cancel(promise)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(10)
def test_multiple_publishers_same_connection():
    """
    Test locking. Publish multiple messages on the same connection
    in different threads.
    """
    conn = app.app.get_amqp_pool().connection()
    messages = ['pub' + str(i) for i in range(5)]

    results = Queue()

    def recv_callback(result):
        log.debug('received result: %r', result)
        result.ack()
        results.put(result.body)

    # register consumer with callback
    consume_promise = conn.consume(queue="listener1",
        callback=recv_callback)

    # publish messages in different gevent threads
    publishers = []
    for msg in messages:
        g = gevent.spawn(conn.publish, exchange="unit_test_room",
            routing_key="user1", body=msg)
        publishers.append(g)

    gevent.joinall(publishers)

    # check that we got all messages back
    result_msgs = set()
    i = 0
    while i < len(messages):
        result = results.get(timeout=5)
        result_msgs.add(result)
        i += 1

    assert result_msgs == set(messages)
    conn.cancel(consume_promise)


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(10)
def test_register_listener_api_method():
    conn = app.app.get_amqp_pool().connection()
    messages = set(['Message ' + str(i) for i in range(10)])
    received_queue = Queue()

    def do_publish():
        import time
        for msg in messages:
            conn.publish(exchange="unit_test_room",
                routing_key="user1", body=msg)
            log.debug('Published message: %r' % msg)
            time.sleep(0.1)

    def recv_callback(result):
        log.debug('Result received: %r', result.body)
        received_queue.put(result.body)
        result.ack()

    app.app.register_and_spawn_amqp_listener('listener1', recv_callback)

    log.debug('Now publishing')
    do_publish()

    received_messages = set()
    while len(received_messages) < 10:
        received_messages.add(received_queue.get())
    eq_(messages, received_messages)
    log.debug('Finished test_register_listener_api_method')


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(10)
def test_multiple_listeners_api_method():
    conn = app.app.get_amqp_pool().connection()
    messages = set(['Message ' + str(i) for i in range(10)])
    received_queue = Queue()

    def do_publish():
        import time
        for msg in messages:
            conn.publish(exchange="unit_test_room",
                routing_key="user1", body=msg)
            log.debug('Published message: %r' % msg)
            time.sleep(0.1)

    def recv_callback1(result):
        log.debug('First consumer received: %r' % result.body)
        received_queue.put(result.body)
        result.ack()

    def recv_callback2(result):
        log.debug('Second consumer received: %r' % result.body)
        received_queue.put(result.body)
        result.ack()

    def recv_callback3(result):
        log.debug('Third consumer received: %r' % result.body)
        received_queue.put(result.body)
        result.ack()

    app.app.register_and_spawn_amqp_listener('listener1', recv_callback1)
    app.app.register_and_spawn_amqp_listener('listener1', recv_callback2)
    app.app.register_and_spawn_amqp_listener('listener1', recv_callback3)

    log.debug('Now publishing')
    do_publish()

    received_messages = set()
    while len(received_messages) < 10:
        received_messages.add(received_queue.get())
    eq_(messages, received_messages)
    log.debug('Finished test_multiple_listeners_api_method')


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(5)
def test_callback_can_call_blocking_methods():
    """Test that a callback can call blocking methods

    The pitfall is that a callback is dispatched by a dispatcher greenlet, and
    if that greenlet blocks waiting for a result from its own connection, it
    won't be able to unblock itself.

    Therefore in this test we do a blocking publish call from a callback.

    Three messages are sent:

    - initial: triggers the callback
    - callback: causes the dispatcher to block holding the connection lock
    - outer: publish a message, in order to wait for the connection lock

    If callback blocks, outer will never complete. We give the whole test 5
    seconds to complete - if it is not complete within this time, we consider
    it hung.

    """
    pool = app.app.get_amqp_pool()
    conn = pool.connection()

    def publish(message):
        """Publish helper - publish to the queue listener1."""
        conn.publish(
            exchange='unit_test_room',
            routing_key='user1',
            body=message
        )

    received = []

    def callback(result):
        """In the callback, publish to our own connection."""
        received.append(result.body)
        result.ack()
        if result.body != 'callback':
            result.reply(body='callback')

    timeout = gevent.Timeout(seconds=5)
    try:
        timeout.start()
        conn.consume(queue='listener1', callback=callback)
        publish('initial')
        publish('outer')
        outer_publisher = gevent.spawn_later(1, publish, 'outer')
        outer_publisher.join()
    except gevent.Timeout:
        # We've deadlocked the connection - we should try to close it
        # But it probably won't close - so we kill everything instead
        gevent.killall([conn.dispatcher, conn.greenlet], block=True, timeout=2)
        try:
            pool.pool.remove(conn)
        except Exception:
            pass

        raise AssertionError("Callback appears hung after 5 seconds.")
    finally:
        timeout.cancel()

    eq_(set(received), set(['initial', 'callback', 'outer']))


@with_setup(amqp_setup, amqp_teardown)
@with_timeout(10)
def test_cancel_consume():
    """Test that we can cancel consuming."""

    pool = app.app.get_amqp_pool()
    conn = pool.connection()
    for c in range(10):
        conn.publish(
            exchange='unit_test_room',
            routing_key='user1',
            body=str(c)
        )

    results = []

    def callback(msg):
        results.append(int(msg.body))
        promise = conn.conn.promises.by_number(msg['promise_number'])
        if msg.body == '5':
            print "Before cancel", promise.refcnt
            msg.cancel_consume()
        print "Before ack", promise.refcnt
        msg.ack()

    conn.consume(queue='listener1', callback=callback, prefetch_count=1)
    gevent.sleep(3)  # wait for messages to be delivered

    eq_(results, [0, 1, 2, 3, 4, 5])

