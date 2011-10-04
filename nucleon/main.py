#!/usr/bin/python

"""Spike of a VREG REST API using gevent for event-based concurrency.

gevent has particularly good performance characteristics according to
http://nichol.as/benchmark-of-python-web-servers
"""

from gevent.pywsgi import WSGIServer


def bootstrap_gevent():
    # Patch the standard library to use gevent
    import gevent.monkey
    gevent.monkey.patch_all()

    # Patch psycopg2 to use gevent coroutines instead of blocking
    import psyco_gevent
    psyco_gevent.make_psycopg_green()


def serve():
    """Start the server. Does not return."""

    from .application import app
    with open('logs/vreg.log', 'w') as f:
        server = WSGIServer(('0.0.0.0', 8888), app, log=f)
        server.serve_forever()


if __name__ == '__main__':
    bootstrap_gevent()
    serve()
