import re
import json
from webob import Request, Response
from webob import exc
import traceback


__all__ = ['Http404', 'JsonResponse', 'JsonErrorResponse', 'Application']

class Http404(Exception):
    """Views can raise this and it will be converted to a JSON 404 error."""


class JsonResponse(Response):
    """A response that converts its body to JSON."""
    def __init__(self, obj, **kwargs):
        ps = {
            'content_type': 'application/json'
        }
        ps.update(kwargs)
        super(JsonResponse, self).__init__(json.dumps(obj), **ps)


class JsonErrorResponse(JsonResponse):
    def __init__(self, obj, **kwargs):
        super(JsonErrorResponse, self).__init__(obj, status=400, **kwargs)


class Application(object):
    """Connects URLS to views and dispatch requests to them."""
    def __init__(self):
        self.routes = []

    def view(self, pattern, **vars):
        def _register(view):
            self.add_view(pattern, view, **vars)
            return view
        return _register

    def add_view(self, pattern, view, **vars):
        self.routes.append((re.compile('^%s$' % pattern), view, vars))

    def configure_database(self, **kwargs):
        self.db = PostgresConnectionPool(**kwargs)

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

