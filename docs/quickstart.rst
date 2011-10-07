Getting started with Nucleon
============================

Starting a new nucleon app is easy. Just type::

    $ nucleon new

to set up a basic nucleon project. Then just run::

    $ nucleon start

in the same directory to start the server. You should be able to see the
nucleon app running by visiting http://localhost:8888/ in your web browser.

An example application
----------------------

Let's go through the process of building a nucleon application. We will choose
a simple example of a shared to-do list.

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

Let's add a view to post a new task. Open up ``app.py``. After the
bootstrapping code that sets up the app is a suitable place to start writing
views. The first view we need is one to retrieve the tasks::

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
