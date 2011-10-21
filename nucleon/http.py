import json
from webob.exc import *
from webob import Request, Response


class Http404(Exception):
    """A "not found" error that can be raised within views.
    
    Http404 will be caught by Nucleon, and an HTTP 404 Not Found response
    served to the client.
    
    """


class JsonResponse(Response):
    """A response that converts its body to JSON."""
    def __init__(self, obj, **kwargs):
        """Construct a JSON response.

        obj should be a structure of primitive Python types that can be
        serialised as JSON (ie. using json.dumps).

        """
        ps = {
            'content_type': 'application/json'
        }
        ps.update(kwargs)
        super(JsonResponse, self).__init__(json.dumps(obj), **ps)


class JsonErrorResponse(JsonResponse):
    """An HTTP 400 error response with a JSON body."""
    def __init__(self, obj, **kwargs):
        super(JsonErrorResponse, self).__init__(obj, status=400, **kwargs)

