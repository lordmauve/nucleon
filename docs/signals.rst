Using Signals
=============

Often it is necessary for operations to be performed at particular points in the
lifecycle of an application.

To allow the developer to register code to be called at these points in the
lifecycle, Nucleon provides a system of signal registration and dispatch.

Signal Registration
-------------------

.. automodule:: nucleon.signals

.. autoclass:: nucleon.signals.Signal

    .. automethod:: connect

    Note that ``Signal`` itself is a callable shortcut for ``connect()``. This
    makes it possible to use a signal as a decorator::

        my_event = Signal()
        @my_event
        def handle_my_event(...):
            ...

    .. automethod:: disconnect
    .. automethod:: fire
    .. automethod:: fire_async


Predefined Signals
------------------

Several signals are predefined that will be called by the nucleon framework at
appropriate times during the application lifecycle. They will also be called
when at appropriate times when running tests, though the testing lifecycle may
be subtly different [#]_.

.. py:data:: nucleon.signals.on_initialise

    Fired before the application has started. Callbacks receive no arguments.

.. py:data:: nucleon.signals.on_start

    Fired when the web application has started and is accepting requests.
    Callbacks receive no arguments.


Example Usage
-------------

To register a signal handler that logs that the application is accepting
requests::

    import logging
    from nucleon.signals import on_start

    @on_start
    def log_ready():
        logging.info("Application started")


.. rubric:: Footnotes

.. [#] In particular, ``nucleon.signals.on_start`` will always be called before
    any tests are executed, whereas in production requests may be processed
    before the ``on_start`` event is finished dispatching.
