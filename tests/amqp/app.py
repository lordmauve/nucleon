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
