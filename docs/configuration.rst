Configuring Nucleon Applications
================================

A Nucleon app's configuration is loaded from a file named ``app.cfg``, which
must reside in the same directory as the application's ``app.py``. The
configuration file is in standard Python `ConfigParser`_ format.

Settings are loaded from sections within the configuration file named by
environment - different environments (demo, staging, qa, production, etc.) may
well have different connection settings for databases, queues, services and so
on. Each application is configured at start time to use settings for a
particular environment.


.. _`ConfigParser`: http://docs.python.org/library/configparser.html

Selecting an environment
------------------------

The default environment is called 'default' and so is loaded from the
configuration file section named ``[default]``.

However, when running tests, settings are loaded from the ``test`` environment.
This switch is currently enacted by calling :py:func:`nucleon.tests.get_test_app()`.

Configuration API
-----------------

In an application, settings for the current environment can be retrieved as
properties of a global settings object.

.. py:data:: nucleon.config.settings

    A global settings object that reflects the current environment.

    Config variables are available as properties of this object.

    .. py:attribute:: environment

        The name of the currently active environment.

    .. py:method:: _set_environment(environment)

        Change to a different environment.
        
        This method will raise ConfigurationError if any settings have been
        read. The alternative could allow the application to become partially
        configured for multiple different environments at the same time, and
        pose a risk of accidental data loss.

For example, reading the currently configured database is as simple as::

    from nucleon.config import settings
    print settings.database
   

.. _database-configuration:

Database access credentials
---------------------------

Databases can be configured for each environment by using the following syntax::

    [environment]
    database = postgres://username:password@host:5432/databasename

'database' is not a special name - just the default. Specific database
connections can be requested by passing the name of their configuration setting
when retrieving a connection pool from the app with
:py:meth:`nucleon.framework.Application.get_database`. Thus a Nucleon app can easily use
connections to multiple databases (albeit with a risk of deadlocks if greenlets
require exclusive use of connections on multiple databases).

Nucleon can manage the set up of database tables and inserting initial data.
This is achieved using the commandline tools - see :doc:`commands` for full
details.

