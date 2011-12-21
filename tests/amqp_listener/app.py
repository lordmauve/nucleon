"""An example Nucleon application."""

__version__ = '0.0.1'


from nucleon.framework import Application
import logging
import gevent
log = logging.getLogger(__name__)
app = Application()


# Uncomment and edit this line to set up the application database
# db = app.setup_database(
#    username='me',
#    password='P455w0rd',
#    database='nucleon'
# )


# Import views and configure the URL space below
#
# from mycomponent import this_view, that_view, post_this_view
#
# app.add_view('/this', {'GET': this_view, 'POST': post_this_view})
# app.add_view('/that/(.*)', that_view)


# Also, you can write your views inline, as below

@app.view('/')
def version(request):
    """An example view that returns the version of the app."""
    return {'version': __version__}


@app.on_start
def configure_amqp():
    with app.get_amqp_pool(type="listen").connection() as connection:
        promise = connection.exchange_declare("test_room")
        connection.wait(promise)

        promise = connection.queue_declare(queue='listenerA')
        connection.wait(promise)

        promise = connection.queue_declare(queue='listenerB')
        connection.wait(promise)

        promise = connection.queue_bind(queue="listenerA", exchange="test_room", routing_key="window")
        connection.wait(promise)

        promise = connection.queue_bind(queue="listenerB", exchange="test_room", routing_key="door")
        connection.wait(promise)


@app.on_start
def start_listener_thread_easy_way():
    """
    recommended pattern
    """

    def print_message(connection,promise,message):
        print "Received on A %s" % message
        connection.basic_ack(message) #remember to ack/reject the message

    app.register_and_spawn_amqp_listener(queue='listenerA', message_callback=print_message)


@app.on_start
def start_listener_thread_raw_way():
    """
    raw access pattern
    """
    log.debug("start_listener_thread")

    def listen_for_listener():

        def listener_cb(promise,message):
            print "Received on B %s" % message
            connection.basic_ack(message) #remember to ack/reject the message

        with app.get_amqp_pool(type="listen").connection() as connection:
            connection.basic_consume(queue='listenerB',callback=listener_cb)
            app._registered_amqp_listeners.append((connection, None))
            print "Listening on amqp for listenerB"
            connection.loop()
            print "Ending listenerB"

    g1 = gevent.spawn(listen_for_listener)
    app._registered_amqp_listeners.append((None, g1))
