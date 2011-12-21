AMQP Access Layer
==========================

Nucleon includes a wrapper for the puka AMQP driver that shares pools of AMQP
connections between greenlets. The number of connections and connection preferences
(user, pass, host, port, vhost) are defined in ``app.cfg`` file.

Publishing AMQP message
-----------------------

All operations can be either synchronously or asynchronously. In case of async
user is required to provide callback functions.

A recommended pattern for sending::

    with app.get_amqp_pool().connection() as conn:
        conn.basic_sync_publish(exchange="unit_test_room",routing_key="user1",body="WithHello1")


.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: basic_sync_publish

A trickier async sending pattern::

    sent_results = Queue()
    def sent_callback(promise,result):
        sent_results.put(result)

    with app.app.get_amqp_pool().connection() as conn:
        conn.basic_async_publish(exchange="unit_test_room",routing_key="user1",body="WithHello1",callback=sent_callback)
        sent = sent_results.get()


.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: basic_async_publish

Warning: remember to wait for all callbacks before you leave the context.

.. class:: nucleon.framework.Application

    .. automethod:: get_amqp_pool

.. class:: nucleon.amqp.pool.DictEntryPool

    .. automethod:: connection


Receiving AMQP messages
-----------------------

In case of messages you can wait either for one message synchronously/asynchronously or just create listening daemon.

.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: basic_async_get_and_ack

    .. automethod:: basic_sync_get_and_ack

Simple one message synchronous listen::

    with app.app.get_amqp_pool(type="listen").connection() as conn:
        resp = conn.basic_sync_get_and_ack(queue="listener1")


Tricker async listening::

    recv_results = Queue()
    def recv_callback(promise,result):
        recv_results.put(result)
        log.debug("Received result %s" % result)

    with app.app.get_amqp_pool(type="listen").connection() as conn:
        conn.basic_async_get_and_ack(queue="listener1",callback=recv_callback)
        recv = recv_results.get()

Warning: remember to wait for all callbacks before you leave the context.

A recommended pattern to create daemon handling incoming messages::

    @app.on_start
    def start_listener_thread():

        def print_message(connection,promise,message):
            print "Received on A %s" % message
            connection.basic_ack(message) #remember to ack/reject the message

        app.register_and_spawn_amqp_listener(queue='listenerA', message_callback=print_message)


Configuring AMQP
----------------

By default two pools are pre-configured. One for listening and one for publishing. You define them in ``app.cfg``.

Remember to make sure that you have all exchanges, queues and bindings defined before you start the code.
A nice pattern is to create @app.on_start function that prepares all configuration::

    @app.on_start
    def configure_amqp():
        log.debug("configure_amqp")
        with app.get_amqp_pool().connection() as connection:
            promise = connection.exchange_declare("unit_test_room")
            connection.wait(promise)

            promise = connection.queue_declare(queue='listener1')
            connection.wait(promise)

            promise = connection.queue_declare(queue='listener2')
            connection.wait(promise)

            promise = connection.queue_bind(queue="listener1", exchange="unit_test_room", routing_key="user1")
            connection.wait(promise)

            promise = connection.queue_bind(queue="listener2", exchange="unit_test_room", routing_key="user2")
            connection.wait(promise)

