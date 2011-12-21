Nucleon Management Commands
===========================

Nucleon has a basic command line interface for managing applications and databases.

Most commands operate on the nucleon application in the current directory, but
will also work if called from a parent directory.

.. program:: nucleon

Application Management
----------------------

.. option:: new <dest>

Sets up the initial structure of a nucleon application in the named directory.

.. option:: start

Start the nucleon application.

By default, nucleon's web service is available on port 8888.

Database Management
-------------------

.. option:: syncdb

Creates any database tables listed in ``database.sql`` that do not already exist,
and also performs INSERTs into the tables that it creates.

.. option:: resetdb

Runs the ``database.sql`` script. Any tables that already exist are dropped and
re-created.

Graceful Application Exit
-------------------------
To close nucleon app in production environment please send it a SIGUSR1 message.
Within 10 seconds timeout (default timeout) nucleon will:

#. Stop serving new pages. All requests during shutdown will be handled with 503 response.
#. Wait for existing requests to complete.
#. Stop receiving new messages if amqp listening loop is configured.
