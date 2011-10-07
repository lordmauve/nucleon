Getting started with Nucleon
============================

Starting a new nucleon app is easy. Just type::

    $ nucleon new

to set up a basic nucleon project.

You should then see several files in your project directory:

* ``app.py`` - the application setup - :doc:`views <framework>` can be written here.
* ``database.sql`` - an SQL script to create database tables and initial data
* ``tests.py`` - a suitable place to write `nose tests`_.

Then just run::

    $ nucleon start

in the same directory to start the server. You should be able to see the
nucleon app running by visiting http://localhost:8888/ in your web browser. In
the default setup, the version of the application is displayed as a JSON
document.

.. _`nose tests`: http://readthedocs.org/docs/nose/en/latest/

An example application
----------------------

Let's go through the process of building a nucleon application. Let's imagine
we have a small list of countries that we can trade with, and we want this
information to be available as a web service for other services to query.

Having set up an application you can immediately start writing views (functions
that process web requests) by editing ``app.py``.  Let's do that now. After the
bootstrapping code that sets up the app is a suitable place to start writing
views.

First, let's set up the data we are going to serve::

    COUNTRIES = {
        'gb': {
            'name': "United Kingdom",
            'language': 'en-GB',
            'currency': 'GBP'
        },
        'fr': {
            'name': "France",
            'language': 'fr-FR',
            'currency': 'EUR'
        }
    }

Then we can add a couple of views on this data. First, other services may want
to know our country codes::

    @app.view('/countries/')
    def countries(request):
        return COUNTRIES.keys()

This view, which can be accessed under ``/countries/``
(http://localhost:8888/countries/ if you are following along!), is simply a
JSON list of country codes!

Another view we might want to support is a view for getting full information on
a country. Let's write that view now::

    from nucleon.http import Http404

    @app.view('/countries/([a-z]{2})/')
    def country(request, code):
        try:
            return COUNTRIES[code]
        except KeyError:
            raise Http404('No such country with the code %s.' % code)

The regular expression in the ``app.view()`` decorator means that this view will
be called to handle requests for ``/countries/<code>/`` where ``code`` is a 2-letter
country code. For example, we can request ``/countries/gb/`` and the response JSON document will be

.. code-block:: javascript

    {
        "name": "United Kingdom",
        "language": "en-GB",
        "currency": "GBP"
    }

Our first database app
----------------------

Let's now try to write a shared to-do list. Unlike the above application, this
will require persistence. nucleon can be integrated with a variety of different
NoSQL stores, but particular attention has been paid to its integration with
the PostgreSQL database, such that multiple greenlets can execute SQL statements
in the database at the same time.

The first thing we should do is open ``database.sql`` and add write some SQL
statements (using any PostgreSQL syntax you like) to configure the required
database table:

.. code-block:: sql

   CREATE TABLE tasks (
       id SERIAL PRIMARY KEY,
       title VARCHAR(255) NOT NULL,
       description TEXT,
       complete BOOLEAN NOT NULL DEFAULT FALSE;
   );

We can have nucleon create this table by running::

    $ nucleon initdb

Adding views
''''''''''''

Let's add a view to post a new task. Open up ``app.py``. The first view we need
is one to retrieve the tasks::

    from nucleon.database.shortcuts import db_select_list
    @app.view('/todo')
    def get_tasks(request):
        return db_select_list('SELECT id, title, complete FROM tasks')

Huh? That was simple. So what have we written?

1. We have written a view for the URL path ``/todo`` (when requested with HTTP
   ``GET``).
2. This returns a list of dictionaries. Each dictionary has keys ``id``,
   ``title``, and ``complete``.

What happens when we request this URL? The response document is

.. code-block:: javascript

    []
