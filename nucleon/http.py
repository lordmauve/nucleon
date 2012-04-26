import datetime
import json
from webob import Response


class HttpException(Exception):
    """
    Abstract HttpException.

    It is a common practice to add status_code field
    """
    def response(self, request):
        """
        Returns Response object that shall be returned to user
        """
        raise NotImplementedError()


class Http404(HttpException):
    """
    A "not found" error that can be raised within views.

    Http404 will be caught by Nucleon, and an HTTP 404 Not Found response
    served to the client.

    """

    def __init__(self, message):
        super(Http404, self).__init__(message)

    def response(self, request):
        """
        Returns JsonResponse with status_code = 404

        Example outputs:
        {
            'error': 'NOT_FOUND',
            'message': 'argument passed to exception'
        }
        """
        msg = {
            'error': 'NOT_FOUND',
            'message': self.args[0]
        }
        return JsonResponse(msg, status=404)


class Http503(HttpException):
    """
    A "Service Unavailable" error.

    The server is currently unable to handle the request due to a temporary
    overloading or maintenance of the server. The implication is that this
    is a temporary condition which will be alleviated after some delay.
    If known, the length of the delay MAY be indicated in a Retry-After header.
    If no Retry-After is given, the client SHOULD handle the response
    as it would for a 500 response.

    """
    status_code = 503

    def __init__(self, *args, **kwargs):
        '''
        Overrides Exception __init__ to pop optional retry_after

        Arguments

        :retry_after: when shall client retry the query

        all remaining arguments are passed as a message response
        '''
        if kwargs.has_key('retry_after'):
            self.retry_after = kwargs.pop('retry_after')
        else:
            self.retry_after = None
        super(Http503, self).__init__(*args, **kwargs)

    def response(self, request):
        """
        Returns JsonResponse with status_code = 503.

        If retry_after is provided than response header will be extended with this field.

        Example outputs:
        {
            'error': 'NOT_FOUND',
            'message': 'argument passed to exception'
        }
        {
            'error': 'NOT_FOUND',
            'message': ['argument1 passed to exception', 'argument 2', ...]
        }
        """
        msg = {'error': 'SERVICE_UNAVAILABLE'}
        if len(self.args) == 1:
            msg['message'] = self.args[0]
        elif len(self.args) > 1:
            msg['message'] = self.args
        if self.retry_after:
            resp = JsonResponse(msg, status=self.status_code, headerlist=[('Retry-After', self.retry_after)])
        else:
            resp = JsonResponse(msg, status=self.status_code)
        return resp


def serialize_date_to_json(obj):
    """Convert Python datetimes to ISO8601-compatible strings.

    This function is suitable for serialising to JSON Python
    datetime objects such as those retrieved from the DB API.

    """
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.time):
        return obj.replace(microsecond=0).isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    else:
        raise TypeError("Cannot convert %r to JSON" % obj)


class JsonResponse(Response):
    """A response that converts its body to JSON.

    As a convenience to allow Python datetime types to be passed directly from
    the database API to a JsonResponse, this class uses a JSON encoder that
    will serialize these types in ISO8601 format.

    """
    def __init__(self, obj, **kwargs):
        """Construct a JSON response.

        obj should be a structure of primitive Python types that can be
        serialised as JSON (ie. using json.dumps), or serialized with
        serialize_date_to_json.

        """
        ps = {
            'content_type': 'application/json'
        }
        ps.update(kwargs)
        body = json.dumps(obj, default=serialize_date_to_json)
        super(JsonResponse, self).__init__(body, **ps)


class JsonErrorResponse(JsonResponse):
    """An HTTP 400 error response with a JSON body."""
    def __init__(self, obj, **kwargs):
        super(JsonErrorResponse, self).__init__(obj, status=400, **kwargs)
