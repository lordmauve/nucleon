import gevent
from gevent.lock import RLock
from gevent.event import AsyncResult
import gevent.hub
import logging
import select
from functools import partial

from .message import Message


log = logging.getLogger(__name__)


def deprecated(func):
    log.info("WARNING: Function %s is deprecated." % func.__name__)
    return func


class asyncmethod(object):
    """Wrap a Puka method so that it can block if a callback is not given."""
    def __init__(self, name, doc=None):
        self.name = name
        self.__doc__ = doc

    def __get__(self, obj, type=None):
        method = getattr(obj.conn, self.name)
        return partial(
            obj._run_with_callback,
            method
        )


class PukaConnection(object):
    """AMQP Connection wrapper.

    Wraps the puka.Client API so that AMQP calls block, unless a callback is
    specified. Also, the connection is wrapped with appropriate locking to
    allow for the connection to be shared between multiple greenlets.

    This class maintains two greenlets:

    * The loop greenlet processes I/O.
    * The dispatcher greenlet executes callbacks that have been scheduled for
      when AMQP returns a result.

    The dispatcher greenlet uses a system of "abdication" such that if it is
    called to execute a blocking call on the same connection, it is allowed to
    do so, but a new dispatcher is started in its place that will eventually
    unblock it.

    This class is intended to be created via
    nucleon.Application.get_amqp_pool(), rather than directly.

    """
    num = 0

    def __init__(self, pool, conn):
        self.pool = pool
        self.conn = conn
        self.conn._loop_break = False
        self.lock = RLock()
        self.conn_id = PukaConnection.num = PukaConnection.num + 1
        log.info('Starting new AMQP connection %d' % self.conn_id)

        # self.running will contain the promises that are currently being
        # dispatched. This is used to prevent them being re-dispatched if the
        # dispatcher is replaced (because it needs to block)
        self.running = set()

        # Start an initial dispatcher
        self.replace_dispatcher()
        self.greenlet = gevent.spawn(self.loop)

    def _run_blocking(self, method, *args, **kwargs):
        """Run an AMQP method and block until the result is ready."""
        r = AsyncResult()

        def temp_callback(p, res):
            r.set(res)

        with self.lock:
            method(*args,
                callback=temp_callback, **kwargs)

        self.must_now_block()
        return r.get()

    def _run_with_callback(self, method, *args, **kwargs):
        """
        Internal method implements a generic pattern to perform sync and async
        calls to Puka. If callback is provided, it runs in async mode.
        """
        log.debug("%s *%r **%r", method.__name__, args, kwargs)
        try:
            callback = kwargs.pop('callback')
        except KeyError:
            return self._run_blocking(method, *args, **kwargs)
        else:
            with self.lock:
                return method(*args, callback=callback, **kwargs)

    def consume(self, callback=None, *args, **kwargs):
        """
        Register a consumer for an AMQP queue.

        If callback is not provided, returns the result dictionary of the first
        message it receives in the queue.

        Asynchronous mode:
        If a callback function is provided, it runs the consume command returns
        the consume-promise only. The callback function will then be called
        with the result of the consume call.
        """
        log.debug("consume *%r **%r", args, kwargs)
        if not callback:
            r = AsyncResult()

            def temp_callback(p, res):
                if 'body' in res:
                    msg = Message(self, res)
                    log.debug('received %r', msg)
                    r.set(msg)

            with self.lock:
                self.conn.basic_get(
                    callback=temp_callback, *args, **kwargs)

            self.must_now_block()
            result = r.get()
            return result
        else:
            def callback_wrapper(p, res):
                if 'body' in res:
                    msg = Message(self, res)
                    log.debug('received %r', msg)
                    callback(msg)

            with self.lock:
                consume_promise = self.conn.basic_consume(
                                    callback=callback_wrapper, *args, **kwargs)
            return consume_promise

    def ack(self, received_result, *args, **kwargs):
        """
        Acknowlege a message received from AMQP queue.
        'received_result' is the response received from the consume call or
        callback.

        This method does not support asynchronous mode.
        """
        with self.lock:
            self.conn.basic_ack(received_result, *args, **kwargs)
            # Note: because of a bug in Puka library the basic_ack messages
            # are not flushed. https://github.com/majek/puka/issues/3
            # The fixes don't seem to work.
            # So, adding the following line as a fix, until the original bug
            # is fixed.
            self.conn.needs_write()

    exchange_declare = asyncmethod('exchange_declare')
    exchange_delete = asyncmethod('exchange_delete')
    exchange_bind = asyncmethod('exchange_bind')
    exchange_unbind = asyncmethod('exchange_unbind')

    queue_declare = asyncmethod('queue_declare')
    queue_delete = asyncmethod('queue_delete')
    queue_purge = asyncmethod('queue_purge')
    queue_bind = asyncmethod('queue_bind')
    queue_unbind = asyncmethod('queue_unbind')

    publish = asyncmethod('basic_publish')
    cancel = asyncmethod('basic_cancel')
    basic_publish = asyncmethod('basic_publish')
    basic_cancel = asyncmethod('basic_cancel')
    basic_get = asyncmethod('basic_get')
    basic_reject = asyncmethod('basic_reject')
    basic_qos = asyncmethod('basic_qos')

    def close(self):
        """Shut down the connection.

        Shuts down the IO loop and dispatcher, and removes this connection from
        its parent pool.

        This method blocks until the connection is completely closed.

        """
        if self.conn._loop_break:
            return
        logging.info("Closing AMQP connection %d" % self.conn_id)
        self.conn._loop_break = True
        gevent.joinall([self.greenlet, self.dispatcher])
        self.conn.close()
        try:
            self.pool.pool.remove(self)
        except ValueError:
            pass

    def start_dispatcher(self):
        """Dispatch callbacks, intended to be run as a separate greenlet.

        Loops until the connection is closed or the current greenlet is no
        longer the dispatcher. In the latter case, don't execute any more
        callbacks, as they will be executed by the real dispatcher.

        """
        while not self.conn._loop_break:
            for promise in (self.conn.promises.ready - self.running):
                self.running.add(promise)
                try:
                    # Really need raise_errors=True, but they get raised here,
                    # not in the callback.
                    #
                    # It would be nice if errors were raised in the blocked
                    # thread ie. by using AsyncResult.set_exception()
                    self.conn.promises.run_callback(promise,
                        raise_errors=False)
                except Exception:
                    import traceback
                    traceback.print_exc()
                finally:
                    self.running.remove(promise)
                if not self.current_is_dispatcher():
                    # If the current greenlet has been replaced as the current
                    # dispatcher, don't run any more callbacks
                    return

            # FIXME: block until notified. This would require us to wrap
            # puka.promise.PromiseCollection with a Semaphore
            gevent.sleep(0.05)

    def must_now_block(self):
        """Signal that something is about to block on this connection.

        If the current greenlet is the dispatcher, we stop being so, and spawn
        a new dispatcher to provide us with the result we need to unblock
        ourselves.

        """
        if self.current_is_dispatcher():
            self.replace_dispatcher()

    def current_is_dispatcher(self):
        """Return True if the calling greenlet is the dispatcher."""

        return gevent.getcurrent() is self.dispatcher

    def replace_dispatcher(self):
        """Spawn a new dispatcher greenlet, replacing the current one.

        This automatically triggers the old dispatcher to stop dispatching
        after processing the current callback.

        """
        self.dispatcher = gevent.spawn(self.start_dispatcher)

    def loop(self):
        '''
        Wait for any promise. Block forever until loop_break is called.

        This function overrides identical from puka.Connection to:
        - set timeout on select.
        - remove timeout on function execution - use gevent.Timeout instead.
        '''
        conn = self.conn

        td = 0.05
        conn._loop_break = False

        while True:
            if conn._loop_break:
                break

            with self.lock:
                needs_write = conn.needs_write()

            r, w, e = select.select([conn],
                                    [conn] if needs_write else [],
                                    [conn],
                                    td)
            with self.lock:
                if r or e:
                    conn.on_read()
                if w:
                    conn.on_write()

        # Try flushing the write buffer just after the loop. The user
        # has no way to figure out if the buffer was flushed or
        # not. (ie: if the loop() require waiting on for data or not).
        conn.on_write()

    def __getattr__(self, item):
        """
        lock wrapper for raw connection
        """
        with self.lock:
            return getattr(self.conn, item)

    def __getitem__(self, item):
        """
        lock wrapper for raw connection
        """
        with self.lock:
            return self.conn[item]

    def __del__(self):
        """
        Cleanly close connections at the end.
        """
        self.close()
