"""An example Nucleon application."""

__version__ = '0.0.1'


from nucleon.framework import Application
import gevent

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
    print "request start"
    """An example view that returns the version of the app."""
    for x in xrange(3):
        gevent.sleep(1)
        print "request step %s" % x
    print "request end"
    return {'version': __version__}
