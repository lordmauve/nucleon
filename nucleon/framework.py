import re
import os
import gevent
from ConfigParser import NoOptionError

from webob import Request, Response

from .database.pgpool import PostgresConnectionPool
from .http import Http404, Http503, HttpException, JsonResponse
from .amqp.pool import PukaDictPool
from .util import WaitCounter

import traceback

__all__ = ['Application', 'ConfigurationError']

STATE_SERVING = 1
STATE_CLOSING = 2
STATE_CLOSED = 3

RETRY_AFTER_503 = 12

class ConfigurationError(Exception):
    """The application instance was misconfigured."""


class Application(object):
    """Connects URLS to views and dispatch requests to them."""
    def __init__(self):
        """
        Create a blank application configured for environment.

        Don't add any configuration dependent functionality here as configuration section may be overwritten by command line arguments.
        """
        self.routes = []
        if 'NUCLEON_CONFIGURATION' in os.environ:
            self.environment = os.environ['NUCLEON_CONFIGURATION']
        else:
            self.environment = 'default'
        self._dbs = {}
        self.running_state = STATE_SERVING
        self.active_requests_counter = WaitCounter()
        self._registered_amqp_listeners = []

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
        try:
            return self._config.get(self.environment, name)
        except NoOptionError, e:
            raise ConfigurationError(e.args[0])

    def _parse_database_url(self, url):
        """Parse a database URL and return a dictionary.

        If the database URL is not correctly formatted a ConfigurationError
        will be raised. Individual parameters are available in the dictionary
        that is returned.

        """
        regex = (
            r'postgres://(?P<user>[^:]+):(?P<password>[^@]+)'
            '@(?P<host>[\w-]+)(?::(?P<port>\d+))?'
            '/(?P<database>\w+)'
        )
        mo = re.match(regex, url)
        if not mo:
            msg = "Couldn't parse database connection string %s" % url
            raise ConfigurationError(msg)
        params = mo.groupdict()
        params['port'] = int(params['port'] or 5432)
        return params

    def get_database(self, name='database'):
        """Return the database connection pool for a configuration name."""
        try:
            return self._dbs[name]
        except KeyError:
            dbstring = self.get_config_string(name)
            params = self._parse_database_url(dbstring)
            self._dbs[name] = PostgresConnectionPool(**params)
            return self._dbs[name]

    def get_amqp_pool(self,type="publish"):
        """
        Returns AMQP connections pool

        It initializes the pool on first request (configuration is defined in app.cfg)

        Usage:
        
        >>> with app.get_amqp_pool().connection() as conn:
        ...    conn.basic_sync_publish(...)

        """
        URL = "amqp_%s_url" % type
        POOL = "amqp_%s_pool_size" % type
        amqp_url = self.get_config_string(URL)
        amqp_pool_size = int(self.get_config_string(POOL))
        return PukaDictPool(name=type, size=amqp_pool_size, amqp_url=amqp_url, app=self)


    def _register_amqp_listener(self, queue, message_callback, type='listen'):
        """
        Registers AMQP message_callback function as a listener on a queue (synchronous, internal API)

        Arguments:
        queue :
            AMQP queue name (remember to create one first)
        message_callback :
            callback function that will be executed on each receiver message given following arguments message_callback(connection, promise, message)
        type :
            name of a pool to take listener from (defaults to 'listen')
        """
        def listener_callback(promise, message):
            """
            generic callback function that executes provided message_callback(connection, promise, message)
            """
            message_callback(connection, promise, message)

        with self.get_amqp_pool(type=type).connection() as connection:
            connection.basic_consume(queue=queue,callback=listener_callback)
            self._registered_amqp_listeners.append((connection, None))
            print "AMQP listener for queue %s" % queue
            connection.loop()
            print "AMQP listener for queue %s - closed" % queue


    def register_and_spawn_amqp_listener(self, queue, message_callback, type='listen'):
        """
        Registers AMQP message_callback function as a listener on a queue (asynchronous)

        It opens a connection to AMQP server from pool of provided type.
        Than it registers provided message_callback function to be executed on each received message.
        Than it spawns a listening loop for this connection as a separate greenlet.
        Listening connection created that way will be gracefully shut down on nucleon exit.

        Note: Remeber to acknowledge the message in message_callback.

        Usage:

        >>> def print_message(connection,promise,message):
        ...     print "Received on A %s" % message
        ...     connection.basic_ack(message) #remember to ack/reject the message
        ...
        ... register_and_spawn_listener(app, queue='listenerA', message_callback=print_message)


        Arguments

        :queue: AMQP queue name (remember to create one first)
        :message_callback: callback function that will be executed on each receiver message given following arguments message_callback(connection, promise, message)
        :type: name of a pool to take listener from (defaults to 'listen')

        """
        greenlet = gevent.spawn(self._register_amqp_listener,queue,message_callback,type=type)
        self._registered_amqp_listeners.append((None, greenlet))

    def load_sql(self, filename):
        """Load an SQL script from filename.
        
        filename must be a path relative to the directory from which the app
        was loaded.

        """
        from nucleon.database.management import SQLScript
        return SQLScript.open(os.path.join(self._path, filename))

    def stop_serving(self,timeout=None):
        """
        Starts nucleon shutdown procedure and waits for its finish.

        Arguments

        :timeout: timeout to wait for shutdown

        """
        gevent.joinall([
            gevent.spawn(self._stop_serving_requests, timeout=timeout),
            gevent.spawn(self._stop_serving_amqp, timeout=timeout)
            ],timeout=timeout)


    def _stop_serving_requests(self, timeout=None):
        """
        Stops serving new http requests and waits for all existing to finish.

        Arguments

        :timeout: timeout to wait for shutdown

        """
        self.running_state = STATE_CLOSING
        self.active_requests_counter.wait_for_zero(timeout)


    def _stop_serving_amqp(self, timeout=None):
        """
        Stops listening for incoming AMQP messages and waits for all listening loops to finish.

        Arguments

        :timeout: timeout to wait for shutdown

        """
        greenlets = []
        for (connection, greenlet) in self._registered_amqp_listeners:
            if connection is not None:
                connection.loop_break()
            if greenlet is not None:
                greenlets.append(greenlet)
        gevent.joinall(greenlets, timeout=timeout)

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
                resp = Response(tb, status=500, content_type='text/plain')
        return resp

    def _dispatch(self, request):
        """
        Handles a request

        Called by _handle.
        """
        if self.running_state == STATE_CLOSING:
            raise Http503("Shutting down",retry_after=RETRY_AFTER_503)
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
