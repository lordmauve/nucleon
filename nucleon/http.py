import json
from webob.exc import *
from webob import Request, Response


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

