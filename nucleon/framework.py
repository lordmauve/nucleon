import sys
import re
import os
import gevent

from webob import Request, Response

from .database.pgpool import PostgresConnectionPool
from .http import Http404, Http503, HttpException, JsonResponse
from .util import WaitCounter
from .config import settings, ConfigurationError

import traceback


__all__ = ['Application']

STATE_SERVING = 1
STATE_CLOSING = 2
STATE_CLOSED = 3

RETRY_AFTER_503 = 12


class Application(object):
    """Connects URLS to views and dispatch requests to them."""
    def __init__(self):
        """
        Create a blank application.
        """
        self.routes = []
        self._dbs = {}
        self.running_state = STATE_SERVING
        self.active_requests_counter = WaitCounter()

    def view(self, pattern, **vars):
        """Decorator that binds a view function to a URL pattern.

        This view will only be used to serve GET requests. All other methods
        will result in a HTTP response of 405 Method Not Allowed.
        """
        def _register(view):
            self.add_view(pattern, view, **vars)
            return view
        return _register

    def add_view(self, pattern, view, **vars):
        """Bind view functions to a given URL pattern.

        If view is a callable then this will be served when the request path
        matches pattern and the method is GET.

        view can also be a dictionary mapping HTTP methods to different view
        functions.

        Any additional keyword parameters will be passed as keyword parameters
        when the view is requested.
        """
        self.routes.append((re.compile('^%s$' % pattern), view, vars))

    def get_config_string(self, name):
        return getattr(settings, name)

    def get_database(self, name='database'):
        """Return the database connection pool for a configuration name."""
        try:
            return self._dbs[name]
        except KeyError:
            dbstring = self.get_config_string(name)
            self._dbs[name] = PostgresConnectionPool.for_url(dbstring)
            return self._dbs[name]

    def load_sql(self, filename):
        """Load an SQL script from filename.

        filename must be a path relative to the directory from which the app
        was loaded.

        """
        from nucleon.database.management import SQLScript
        return SQLScript.open(os.path.join(self._path, filename))

    def stop_serving(self, timeout=None):
        """
        Starts nucleon shutdown procedure and waits for its finish.

        Arguments

        :timeout: timeout to wait for shutdown

        """
        stop = gevent.spawn(self._stop_serving_requests, timeout=timeout)
        stop.join(timeout=timeout)

    def _stop_serving_requests(self, timeout=None):
        """
        Stops serving new http requests and waits for all existing to finish.

        Arguments

        :timeout: timeout to wait for shutdown

        """
        self.running_state = STATE_CLOSING
        self.active_requests_counter.wait_for_zero(timeout)

    def __call__(self, environ, start_response):
        req = Request(environ)
        resp = self._handle(req)
        return resp(environ, start_response)

    def _handle(self, request):
        """
        Handles a request

        Wraps request handling with WaitCounter and handles all Exceptions
        """
        with self.active_requests_counter:
            try:
                resp = self._dispatch(request)
            except HttpException, e:
                resp = e.response(request)
            except:
                tb = traceback.format_exc()
                print >>sys.stderr, tb
                resp = Response(tb, status=500, content_type='text/plain')
        return resp

    def _dispatch(self, request):
        """
        Handles a request

        Called by _handle.
        """
        if self.running_state == STATE_CLOSING:
            raise Http503("Shutting down", retry_after=RETRY_AFTER_503)
        path = request.path_info
        for regex, view, vars in self.routes:
            match = regex.match(path)
            if match:
                if isinstance(view, dict):
                    try:
                        view = view[request.method]
                    except KeyError:
                        return Response('', allow=view.keys(), status=405)
                elif request.method != 'GET':
                    return Response('', allow=['GET'], status=405)

                args = match.groups()
                resp = view(request, *args, **vars)
                if not isinstance(resp, Response):
                    resp = JsonResponse(resp)
                return resp
        else:
            raise Http404("No pattern matches this URL.")
