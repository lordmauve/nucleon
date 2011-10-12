Coroutine-based concurrency with gevent
=======================================

Nucleon is tightly integrated with the `gevent`_ library, which makes it possible
to perform multiple IO operations apparently concurrently, without the overhead of
operating system threads.

.. _`gevent`: http://www.gevent.org/

This model of programming can require a different way of thinking.
Specifically, unless a greenlet yields control either explicitly or by blocking
on something, it will block everything else happening anywhere else in the
nucleon application. For example an operation that takes 1 second to complete
prevents any other requests from being served for a whole second, even if those
operations would consume a tiny amount of CPU time. This could cause severe
performance problems.

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

    You should also watch out for unexpected DNS activity.

To use gevent to best effect you should try to ensure that CPU is used in very
short bursts so that the processing of other requests can be interleaved.

Diagnosing blocking calls
-------------------------

The Linux ``strace`` command can be used to print out the system calls used by
a nucleon application.

.. code-block:: bash

    $ strace -T nucleon start

The ``-T`` option will make strace display the time spent in each system call -
pay attention to any calls with particularly large values, other than
``epoll_wait()`` (which is how gevent stops when all greenlets are blocked).

Undertaking more expensive processing
-------------------------------------

If you do need to use more CPU time very rarely, then it's possible to
mitigate the impact to other requests running at the same time.

The most direct way to do this is to explicitly yield control from within a
greenlet. gevent will run any other greenlets that can run before returning
control to the yielding greenlet. This is most similar to conventional
threading.

A more elegant way to do this is to use a map-reduce model. In the map phase, a
greenlet breaks up a task into many component tasks. These are each put onto a
queue. Other greenlets pick up a task and execute them. The results are also
put back into a queue. In the reduce phase some greenlet blocks waiting for
responses and combines the results. Writing a task in this way can give
extremely good scalability.

In-memory Persistence
---------------------

Nucleon runs in a single native thread in a single process, with all greenlets
sharing the same memory space. Because of this, Nucleon apps can store data in
application memory. No synchronisation primitives are required, so long as your
application code never performs leaves the memory space in an inconsistent
state while blocking IO operations are being performed.

Ensuring this is the case is preferable to using ``gevent.coros`` classes for
locking, as this will simply reduce the number of greenlets eligible to run to
completion while the greenlet holding the lock is blocked on I/O.
