Coroutine-based concurrency with gevent
=======================================

Nucleon is tightly integrated with the `gevent`_ library, which makes it possible
to perform multiple IO operations apparently concurrently, without the overhead of
operating system threads.

.. _`gevent`: http://www.gevent.org/

This model of programming can require a different way of thinking.
Specifically, every operation that is performed in CPU will block everything
else happening anywhere else in the nucleon application. For example an
operations that takes 1 second to complete prevents any other requests from
being served for one second, even if those operations would consume a tiny
amount of CPU time. This could cause severe performance problems.

On the other hand, blocking network operations are very efficient. This
includes database operations, REST calls, or communication with AMQP. gevent
patches Python so that instead of blocking, other operations will be processed
*as if in the background*. This includes Python operations that block, as well
as pure Python libraries that use those operations.

.. warning::

    **Native libraries can completely block gevent**. If an external library
    performs some blocking operation, your entire application will grind to a
    halt. You should identify whether the library supports non-blocking IO or
    can be integrated with an external IO loop, before attempting to integrate
    the library.

    You might need to be particularly careful if a library performs I/O as a
    hidden side-effect of it normal operation. Some XML-processing libraries,
    for example, may make web requests for DTDs in order to correctly process
    an XML document.

    You should also watch out for DNS activity.

To use gevent to best effect you should try to ensure that the minimum amount
of CPU is used as glue between blocking network operations. CPU heavy tasks
should be handled outside of your nucleon application, perhaps by a backend
worker that listens for requests on AMQP.

Diagnosing blocking calls
-------------------------

The Linux ``strace`` command can be used to print out the system calls used by
a nucleon application.

.. code-block:: bash

    $ strace -T nucleon start

The ``-T`` option will make strace display the time spent in each system call -
pay attention to any calls with particularly large values, other than
``epoll_wait()`` (which is how gevent stops when all greenlets are blocked).

In-memory Persistence
---------------------

Because Nucleon runs single-threaded in a single process, each nucleon instance
uses one memory space for all requests. Because of this, Nucleon apps can store
data in application memory. No synchronisation primitives are required, so long
as your application code never performs leaves the memory space in an
inconsistent state while blocking IO operations are being performed.
