import re
import traceback
from ConfigParser import NoOptionError


from webob import Request, Response

from .database.pgpool import PostgresConnectionPool
from .http import Http404, JsonResponse 


__all__ = ['Application', 'ConfigurationError']



class ConfigurationError(Exception):
    """The application instance was misconfigured."""


class Application(object):
    """Connects URLS to views and dispatch requests to them."""
    def __init__(self, environment='default'):
        """Create a blank application configured for the specified environment."""
        self.routes = []
        self.environment = environment
        self._dbs = {}

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
        mo = re.match(r'postgres://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[\w-]+)(?::(?P<port>\d+))?/(?P<database>\w+)', url)
        if not mo:
            raise ConfigurationError("Couldn't parse database connection string %s" % dbstring)
        params = mo.groupdict()
        params['port'] = int(params['port'] or 5432)
        return params

    def get_database(self, name='database'):
        import re
        try:
            return self._dbs[name]
        except KeyError:
            dbstring = self.get_config_string(name)
            params = self._parse_database_url(dbstring)
            self._dbs[name] = PostgresConnectionPool(**params)
            return self._dbs[name]

    def __call__(self, environ, start_response):
        req = Request(environ)
        resp = self._dispatch(req)
        return resp(environ, start_response)

    def _dispatch(self, request):
        try:
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
        except Http404, e:
            emsg = {'error': 'NOT_FOUND'}
            if len(e.args):
                emsg['message'] = e.args[0]
            return JsonResponse(emsg, status=404)
        except:
            tb = traceback.format_exc()
            return Response(tb, status=500, content_type='text/plain')

