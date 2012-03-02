"""An example Nucleon application."""

__version__ = '0.0.1'


from nucleon.framework import Application
from nucleon.signals import on_initialise
import logging
from gevent.queue import Queue
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


@app.view('/push')
def push(request):
    """
    view for performance tests
    """
    sent_results = Queue()
    recv_results = Queue()

    def sent_callback(promise, result):
        sent_results.put(result)
        log.debug("Received result %s" % result)

    def recv_callback(promise, result):
        recv_results.put(result)
        log.debug("Received result %s" % result)

    conn = app.get_amqp_pool().connection()
    connR = app.get_amqp_pool(type="listen").connection()
    conn.publish(exchange="unit_test_room",
        routing_key="user1", body="Ping Message", callback=sent_callback)
    connR.consume(queue="listener1", callback=recv_callback)

    recv = recv_results.get()
    sent = sent_results.get()

    return {'value': recv['body']}

@app.view('/push_sync')
def push_sync(request):
    """
    view for performance tests
    """
    conn = app.get_amqp_pool().connection()
    connR = app.get_amqp_pool(type="listen").connection()
    sent = conn.publish(exchange="unit_test_room",
        routing_key="user1", body="Ping Message")
    recv = connR.consume(queue="listener1")

    return {'value': recv['body']}

@on_initialise
def configure_amqp():
    log.debug("configure_amqp")
    connection = app.get_amqp_pool().connection()

    # Delete the queues if they are already there
    try:
        connection.queue_delete(queue='listener1')
    except Exception as e:
        print "Setup AMQP: No pre-existing queue listener1"

    try:
        connection.queue_delete(queue='listener2')
    except Exception as e:
        print "Setup AMQP: No pre-existing queue listener2"

    connection.queue_declare(queue='listener1')

    connection.queue_declare(queue='listener2')

    connection.queue_bind(queue="listener1", exchange="unit_test_room",
        routing_key="user1")

    connection.queue_bind(queue="listener2", exchange="unit_test_room",
        routing_key="user2")