Database Configuration
======================

A Database Configuration example resides in ``nucleon/skel/app.cfg`` and a typical line would look like this:

``database = postgres://username:password@host:5432/databasename``

where the username, password, host, port and datbasename should be specified and the app.cfg file should be placed in your application folder.

Database initialisation is achieved via puppet and this should include creating the database(s) and grant statements.

Once created, Nucleon allows for database syncronisation using the syncdb command which will drop then create the tables in the database.

Using the database connection
=============================

A ``ConfigurationError`` will be raised when starting the application if the database string is incorrectly formatted.

The method ``get_database`` then returns a list of database connection objects which are derived from psycopg2.connect(). You may then use methods such as cursor() or connection() to perform database operations. An available connection will be used or the call will block until a connection is available.
