Writing REST/JSON Applications
==============================

Nucleon makes it easy to write JSON/REST applications with relatively little
code. The URL routing and view dispatching is modelled on Django's, except that
in Nucleon callables are registered directly with an app rather than being
automatically loaded from a separate URL configuration module.

Views are simply methods that accept a request object as a parameter and return
a response. The response is typically a structure consisting of lists, dicts,
strings, etc., that will be served to the user as JSON.

The other type of response is a ``nucleon.http.Response`` subclass, which allows
a wider variety of return values or response codes.

.. automodule:: nucleon.framework

.. autoclass:: Application

    An Application instance acts as a WSGI-compatible callable, and can be
    wrapped with WSGI-compliant middleware or served using a variety of
    webservers. However it is primarily intended to be served with nucleon's
    in-built gevent web server.

    Views are any callable that accepts an argument ``request``, for example::

        def client_info(request):
            return {
                'ua': request.headers.get('User-Agent', None),
                'ip': request.remote_addr
            }
    
    Views can be registered to be called by an application in response to a
    specific URL, either with the ``view()`` decorator, or by calling
    ``add_view()`` and passing the view to be added. In other words, the
    following are equivalent::

        @app.view('/foo')
        def get_foo(request):
            ...

    versus ::

        def get_foo(request):
            ...

        app.add_view('/foo', get_foo)

    .. automethod:: add_view

    .. automethod:: view


Processing Requests
-------------------



Returning Responses
-------------------

Nucleon includes several classes that can be used as responses, in addition to
returning Python structures to be serialised as JSON. These are all based on
`WebOb Response`_:

.. _`WebOb Response`: http://docs.webob.org/en/latest/reference.html#id2

.. automodule:: nucleon.http

.. autoclass:: nucleon.http.Response
    :members:

A subclass of Response is provided as a convenience for returning a response in
JSON format. This is necessary if you wish to customise the response - for
example, by including different response headers, or to return a different
status code.

.. autoclass:: nucleon.http.JsonResponse

Another convenience is the ability to raise particular exception classes which
will cause Nucleon to serve standard error responses.

.. autoclass:: nucleon.http.Http404
