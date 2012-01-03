#!/usr/bin/python

"""Entry point to a Nucleon application.

This module contains functions for patching gevent and psycopg2, and starting
the Nucleon server.

"""

import gevent

HALT_TIMEOUT = 10

def register_signal(app,server):
    import signal
    def signal_handler():
        print("Got SIGUSR1 - shutting down")
        app.stop_serving(timeout=HALT_TIMEOUT)
        server.stop()
        print("Shutting down complete")
    gevent.signal(signal.SIGUSR1, signal_handler)


def bootstrap_gevent():
    # Patch the standard library to use gevent
    import gevent.monkey
    gevent.monkey.patch_all()

    # Patch psycopg2 to use gevent coroutines instead of blocking
    from nucleon.database import psyco_gevent
    psyco_gevent.make_psycopg_green()


def serve(app, logfile='nucleon.log', host='0.0.0.0', port=8888):
    """Start the server. Does not return."""
    from gevent.pywsgi import WSGIServer
    with open(logfile, 'w') as f:
        server = WSGIServer((host, port), app, log=f)
        app.run_on_start_funcs()
        register_signal(app,server)
        print "Listening on: %s:%s" % (host, port)
        print "Configuration used: %s" % (app.environment)
        server.serve_forever(stop_timeout=5)
