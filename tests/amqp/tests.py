from nose.tools import *
from nucleon import tests
import logging
import gevent
from gevent.queue import Queue
log = logging.getLogger(__name__)
app = tests.get_test_app(__file__)


#can listeners share connection
#can senders share connection -> add lock

#NB: message exchanges are registered at app.py

def test_00_version():
    log.debug("test_0_version")
    resp = app.get('/')
    eq_(resp.json, {'version': '0.0.1'})


def test_01_connections():
    log.debug("test_01_connections")
    p1 = app.app.get_amqp_pool("publish")
    log.debug("p1: %s" % p1)
    p2 = app.app.get_amqp_pool("publish")
    log.debug("p2: %s" % p2)
    eq_(p1, p2)
    p3 = app.app.get_amqp_pool("listen")
    log.debug("p3: %s" % p3)
    assert p1 != p3
    log.debug("connection...")
    eq_(p1.queue.qsize(),5)
    c1 = p1.get_conn()
    eq_(p1.queue.qsize(),4)
    c2 = p1.get_conn()
    eq_(p1.queue.qsize(),3)
    del(c1)
    eq_(p1.queue.qsize(),4)
    del(c2)
    eq_(p1.queue.qsize(),5)
    c3 = p1.get_conn()
    eq_(p1.queue.qsize(),4)


def test_02_connections():
    log.debug("test_02_connections")
    p1 = app.app.get_amqp_pool("publish")
    eq_(p1.queue.qsize(),5)

def test_05_get_publish_connection():
    log.debug("test_05_get_publish_connection")
    with app.app.get_amqp_pool().connection() as conn:
        log.debug("connection: %s" % conn)
        from nucleon.amqp.connection import PukaConnection
        assert isinstance(conn,PukaConnection)


def test_09_publish_sync_get_sync():
    """
    send message on connS1
    receive message on connR1

    send message on connS1
    receive message on connR2
    """
    log.debug("test_09_publish_get_sync")

    with app.app.get_amqp_pool().connection() as connS1:
        with app.app.get_amqp_pool(type="listen").connection() as connR1:
            with app.app.get_amqp_pool(type="listen").connection() as connR2:
                log.debug("connection: %s" % connS1)
                log.debug("connection: %s" % connR1)
                log.debug("connection: %s" % connR2)
                from nucleon.amqp.pool import PukaConnection
                assert isinstance(connS1,PukaConnection)
                assert isinstance(connR1,PukaConnection)
                assert isinstance(connR2,PukaConnection)

                eq_(connS1.basic_sync_publish(exchange="unit_test_room",routing_key="user1",body="Hello my Get1"),{})

                resp = connR1.basic_sync_get_and_ack(queue="listener1")
                eq_(resp['body'],"Hello my Get1")

                eq_(connS1.basic_sync_publish(exchange="unit_test_room",routing_key="user1",body="Hello my Get2"),{})

                resp = connR2.basic_sync_get_and_ack(queue="listener1")
                eq_(resp['body'],"Hello my Get2")


def test_20_publish_async_get_async():
    """
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
    with app.app.get_amqp_pool().connection() as connS1:
        with app.app.get_amqp_pool(type="listen").connection() as connR1:
            with app.app.get_amqp_pool(type="listen").connection() as connR2:
                log.debug("connection: %s" % connS1)
                log.debug("connection: %s" % connR1)
                log.debug("connection: %s" % connR2)
                from nucleon.amqp.pool import PukaConnection
                assert isinstance(connS1,PukaConnection)
                assert isinstance(connR1,PukaConnection)
                assert isinstance(connR2,PukaConnection)

                sent_results = Queue()
                recv_results = Queue()

                def sent_callback(promise,result):
                    sent_results.put(result)
                    log.debug("Received result %s" % result)

                def recv_callback(promise,result):
                    recv_results.put(result)
                    log.debug("Received result %s" % result)


                connS1.basic_async_publish(exchange="unit_test_room",routing_key="user1",body="HelloASync1",callback=sent_callback)
                connR1.basic_async_get_and_ack(queue="listener1",callback=recv_callback)

                recv = recv_results.get()
                sent = sent_results.get()
                eq_(sent, {})
                eq_(recv['body'],"HelloASync1")

                connS1.basic_async_publish(exchange="unit_test_room",routing_key="user1",body="HelloASync2",callback=sent_callback)
                connR2.basic_async_get_and_ack(queue="listener1",callback=recv_callback)

                recv = recv_results.get()
                sent = sent_results.get()
                eq_(sent, {})
                eq_(recv['body'],"HelloASync2")

def test_21_connections():
    """
    let's make sure we have all connections ready in the pools
    """
    log.debug("test_21_connections")
    gevent.sleep(1) #time for gc
    p1 = app.app.get_amqp_pool("publish")
    eq_(p1.queue.qsize(),5)
    p2 = app.app.get_amqp_pool("listen")
    eq_(p2.queue.qsize(),5)

def test_30_with_publish_get_sync():
    log.debug("test_30_with_publish_get_sync")
    with app.app.get_amqp_pool().connection() as conn:
        resp = conn.basic_sync_publish(exchange="unit_test_room",routing_key="user1",body="WithHello1")
        eq_(resp,{})

    with app.app.get_amqp_pool(type="listen").connection() as conn:
        resp = conn.basic_sync_get_and_ack(queue="listener1")
        eq_(resp['body'],"WithHello1")

    with app.app.get_amqp_pool().connection() as conn:
        resp = conn.basic_sync_publish(exchange="unit_test_room",routing_key="user1",body="WithHello2")
        eq_(resp,{})

    with app.app.get_amqp_pool(type="listen").connection() as conn:
        resp = conn.basic_sync_get_and_ack(queue="listener1")
        eq_(resp['body'],"WithHello2")

def test_31_with_publish_get_async():
    log.debug("test_31_with_publish_get_async")

    sent_results = Queue()
    recv_results = Queue()

    def sent_callback(promise,result):
        sent_results.put(result)
        log.debug("Received result %s" % result)

    def recv_callback(promise,result):
        recv_results.put(result)
        log.debug("Received result %s" % result)


    with app.app.get_amqp_pool().connection() as conn:
        with app.app.get_amqp_pool(type="listen").connection() as connR:
            conn.basic_async_publish(exchange="unit_test_room",routing_key="user1",body="WithHello1",callback=sent_callback)
            connR.basic_async_get_and_ack(queue="listener1",callback=recv_callback)

            recv = recv_results.get()
            sent = sent_results.get()
            eq_(sent, {})
            eq_(recv['body'],"WithHello1")

    with app.app.get_amqp_pool().connection() as conn:
        with app.app.get_amqp_pool(type="listen").connection() as connR:
            conn.basic_async_publish(exchange="unit_test_room",routing_key="user1",body="WithHello2",callback=sent_callback)
            conn.basic_async_get_and_ack(queue="listener1",callback=recv_callback)

            recv = recv_results.get()
            sent = sent_results.get()
            eq_(sent, {})
            eq_(recv['body'],"WithHello2")


def test_99_tear_down():
    log.debug("tear_down")
    with app.app.get_amqp_pool().connection() as client:
        try:
            promise = client.exchange_delete("unit_test_room")
            client.wait(promise)
        except Exception as e:
            print e

        try:
            promise = client.queue_delete(queue='listener1')
            client.wait(promise)
        except Exception as e:
            print e

        try:
            promise = client.queue_delete(queue='listener2')
            client.wait(promise)
        except Exception as e:
            print e
