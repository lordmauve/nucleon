AMQP Access Layer
==========================

Nucleon includes a wrapper for the puka AMQP driver that shares pools of AMQP
connections between greenlets. The number of connections and connection preferences
(user, pass, host, port, vhost) are defined in ``app.cfg`` file.

Publishing AMQP message
-----------------------

All operations can be either synchronously or asynchronously. In case of async
user is required to provide callback functions.

Publishing messages synchronously::

    conn = app.get_amqp_pool().connection()
    conn.publish(exchange="unit_test_room", routing_key="user1", body="WithHello1")

.. class:: nucleon.framework.Application

    .. automethod:: get_amqp_pool

.. class:: nucleon.amqp.pool.DictEntryPool

    .. automethod:: connection

.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: publish

Sending messages asynchronously requires using a callback function::

    sent_results = Queue()
    def sent_callback(promise,result):
        sent_results.put(result)

    conn = app.app.get_amqp_pool().connection()
    conn.publish(exchange="unit_test_room", routing_key="user1", 
        body="WithHello1", callback=sent_callback)
    sent = sent_results.get()


.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: publish

Warning: remember to wait for all callbacks before you leave the context.


Receiving AMQP messages
-----------------------

Receiving messages is a four step process:

1. Register your consumer with RabbitMQ. If a callback is not provided, the consume method call returns the first message it receives from the queue. If callback is provided, it is called automatically for every message as it is received.
2. Receive messages by blocking (in synchronous mode) or using callbacks asynchronously.
3. After processing the message, if there were no errors, send an acknowledgement to RabbitMQ that the message has been successfully processed.
4. If in async mode, cancel the consumer.

Synchronous Listening
^^^^^^^^^^^^^^^^^^^^^

In Synchronous listening mode, the ``consume()`` method returns the first result it gets in the queue. There is no need for explicitly cancelling the consumer using the ``cancel()`` call. 

Internally we use the RabbitMQ ``basic_get`` command in this mode.

Receiving a message::

    conn = app.app.get_amqp_pool(type="listen").connection()
    result = conn.consume(queue="listener1")


.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: consume

Note: The ``consume`` method returns the response object when in synchronous mode, and only the ``promise_number`` in asynchronous mode.

Acknowledge processed messages::

    conn.ack(response)

.. class:: nucleon.amqp.connection.PukaConnection

    .. automethod:: ack


Asynchronous Listening
^^^^^^^^^^^^^^^^^^^^^^

To register a new consumer asynchronously, pass a callback function to the consume method. This callback method will then be called for each received message::

    conn = app.app.get_amqp_pool(type="listen").connection()

    recv_results = Queue()
    def recv_callback(promise,result):
        """Callback method for receiving messages"""
        # process message or put in queue for later processing
        recv_results.put(result)
        log.debug("Received result %s" % result)

    # Register consumer with a callback function
    consume_promise = conn.consume(queue="listener1", 
        callback=recv_callback)

    # Read messages from Queue
    recv = recv_results.get()

    # acknowlege that the message was properly processed
    conn.ack(result)

    # cancel the consumer to unregister it from RabbitMQ
    conn.cancel(consume_promise)

Warning: remember to wait for all callbacks before you leave the context.

A recommended pattern to create daemon handling incoming messages::

    from nucleon.signals import on_initialise
    @on_initialise
    def start_listener_thread():

        def recv_callback(connection, promise, result):
            print 'Result received: ' + result['body']
            connection.ack(result)

        app.register_and_spawn_amqp_listener('listener1', recv_callback)

.. class:: nucleon.framework.Application

    .. automethod:: register_and_spawn_amqp_listener

    :noindex:


Configuring AMQP
----------------

By default two pools are pre-configured. One for listening and one for publishing. You define them in ``app.cfg``.

Remember to make sure that you have all exchanges, queues and bindings defined before you start the code.
A nice pattern is to register an `on_initialise` handler that prepares all configuration::

    from nucleon.signals import on_initialise
    @on_initialise
    def configure_amqp():
        log.debug("configure_amqp")
        connection = app.get_amqp_pool().connection()

        connection.exchange_declare("unit_test_room")
        
        connection.queue_declare(queue='listener1')
        
        connection.queue_declare(queue='listener2')
        
        connection.queue_bind(queue="listener1", exchange="unit_test_room", routing_key="user1")
        
        connection.queue_bind(queue="listener2", exchange="unit_test_room", routing_key="user2")
            

Shutting Down
-------------

Before we shutdown the application, it is good practice to remove the exchanges and queues we created::

    log.debug("tear_down")
    conn = app.app.get_amqp_pool().connection()

    client.exchange_delete("unit_test_room")

    client.queue_delete(queue='listener1')
    
    client.queue_delete(queue='listener2')
        