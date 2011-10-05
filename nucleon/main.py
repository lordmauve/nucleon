#!/usr/bin/python

"""Entry point to a Nucleon application.

This module contains functions for patching gevent and psycopg2, and starting
the Nucleon server.

"""

from gevent.pywsgi import WSGIServer


def bootstrap_gevent():
    # Patch the standard library to use gevent
    import gevent.monkey
    gevent.monkey.patch_all()

    # Patch psycopg2 to use gevent coroutines instead of blocking
    import psyco_gevent
    psyco_gevent.make_psycopg_green()


def serve(logfile='nucleon.log', port=8888):
    """Start the server. Does not return."""

    from .application import app
    with open(logfile, 'w') as f:
        server = WSGIServer(('0.0.0.0', port), app, log=f)
        server.serve_forever()


if __name__ == '__main__':
    #TODO: fork/daemonize here - or after binding port?
    bootstrap_gevent()
    serve()
