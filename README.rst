Nucleon
=======

Nucleon is a web microframework, for creating light, fast RESTful services for server-to-server operations.

Problem Domain
--------------

Nucleon was created to simplify the process of creating "back end services" - components that provide REST and AMQP interfaces to each other, to front-end web applications, and rarely to the end user. It is not intended to generate HTML, provide developer utilities like users/cookies/sessions, perform internationalisation, and so on - Django (or your microframework of choice) is already excellent at this.

This kind of back end service components need to be

* Distributed - for the purposes of scalability and availablity.
* Fast - because the back end may be performing dozens of operations for each front-end request.
* RESTful - because it provides a universal, simple interface that works with off-the-shelf caches, load balancers, etc.
* Not limited to REST - specifically, it should be possible to loosely couple components over AMQP.

REST is primarily useful for synchronous operations - "Do this now and hand me back the result."

AMQP gives loose coupling between components - "Something has happened, you may want to deal with it" or "Do this as soon as possible."

About Nucleon
-------------

Nucleon largely consists of glue between existing Python components, primarily gevent, paste, psycopg2, and an AMQP library called Puka.

It is deliberately kept simple, with as few layers of indirection as possible. This comes with limitations:

There is no ORM included. ORMs obfuscate what queries are actually being executed, and fail to expose the most powerful database features.
We don't use any kind of database abstraction layer, and thus (so far) only PostgreSQL is supported.

For more information, `check out the documentation`__.

.. __: http://nucleon.readthedocs.org/
