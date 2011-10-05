import sys
from cStringIO import StringIO

from .. import VERSION


class TestClient(object);
    "Client to make requests to a WSGI app without running it."

    def __init__(self, app):
        self.app = app

    def request(self, method, path, body, headers={}):
        hs = {
            'User-agent': 'Nucleon/%s' % VERSION,
            'Host': 'localhost',
            'Accept': 'application/json; q=1, */*; q=0.1',
        }
        hs.update(headers)
        hs['Content-Length'] = len(body)

        # Set up environ
        if '?' in path:
            path, qs = path.split('?', 1)
        else:
            qs = None

        environ = {
            'REQUEST_METHOD': method,
            'SCRIPT_NAME': '',
            'PATH_INFO': path,
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '443',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': len(body),
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': StringIO(body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': True,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }

        if qs is not None:
            environ['QUERY_STRING'] = qs

        for k, v in hs.items():
            key = 'HTTP_' + k.upper().replace('-', '_')
            environ[key] = v

        if 'HTTP_CONTENT_TYPE' in environ:
            environ['CONTENT_TYPE'] = environ['HTTP_CONTENT_TYPE']
            
        response = [None, None, '']
        def start_response(response_status, response_headers):
            assert isinstance(response_status, str)
            for h in response_headers:
                assert len(h) == 2
            response[0] = response_status
            response[1] = response_headers

        # Collect response body
        for chunk in self.app(environ, start_response):
            response[2] += chunk
        return self.format_response(response)

    def format_response(self, response):
        pass

    def get(self, url, headers={}):
        """Perform a GET request to the application."""

    def post(self, url, params={}, headers={}):
        """Perform a POST request to the application."""
