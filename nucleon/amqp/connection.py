import gevent
from gevent.lock import RLock
from gevent.event import AsyncResult
import logging
import select

log = logging.getLogger(__name__)


def deprecated(func):
    log.info("WARNING: Function %s is deprecated." % func.__name__)
    return func


class PukaConnection(object):
    """
    Puka Connection proxy wrapper
    - provides sync and async wrappers for common functions
    - assures connection reliability through locking
    - async is provided as Greenlets
    Don't initialize directly. Use nucleon.Application.get_amqp_pool()
    """
    def __init__(self, pool, conn):
        self.pool = pool
        self.conn = conn
        self.conn._loop_break = False
        self.lock = RLock()
        print 'PukaConnection.__init__(): conn = ' + str(self.conn)
        self.greenlet = gevent.spawn(self.loop)

    def _run_with_callback(self, method, callback=None, *args, **kwargs):
        """
        Internal method implements a generic pattern to perform sync and async
        calls to Puka. If callback is provided, it runs in async mode.
        """
        if callback:
            with self.lock:
                return method(*args, callback=callback, **kwargs)

        else:
            print '_run_with_callback(): No callback. method =',\
                method.__name__, ' self.conn = ', self.conn

            r = AsyncResult()
            with self.lock:
                def temp_callback(p, res):
                    print 'temp_callback called. p, res = ', p, res
                    r.set(res)
                    promise = self.conn.promises.by_number(p)
                    promise.refcnt_inc()

                method(*args,
                    callback=temp_callback, **kwargs)
            return r.get()

    def publish(self, callback=None, *args, **kwargs):
        """
        Publish a message to AMQP.

        Asynchronous mode:
        Pass a callback function which will be called with the result of the
        publish call.
        """
        return self._run_with_callback(method=self.conn.basic_publish,
                    callback=callback, *args, **kwargs)

    def consume(self, callback=None, *args, **kwargs):
        """
        Register a consumer for an AMQP queue.

        If callback is not provided, returns the result dictionary of the 
        first message it receives in the queue.

        Asynchronous mode:
        If a callback function is provided, it runs the consume command returns
        the consume-promise only. The callback function will then be called
        with the result of the consume call.
        """
        if not callback:
            r = AsyncResult()

            def temp_callback(p, res):
                print 'consume temp_callback called. p, res = ', p, res
                # self.cancel(p)
                r.set(res)
                promise = self.conn.promises.by_number(p)
                promise.refcnt_inc()

            with self.lock:
                promise_number = self.conn.basic_get(
                    callback=temp_callback, *args, **kwargs)
                # promise_number = self.conn.basic_consume(
                #     callback=temp_callback, prefetch_count=1, *args,**kwargs)
                # print "Sync Promise", promise_number

            result = r.get()
            # self.cancel(result['promise_number'])
            return result
        else:
            def callback_wrapper(p, res):
                callback(p, res)
                promise = self.conn.promises.by_number(p)
                promise.refcnt_inc()

            with self.lock:
                consume_promise = self.conn.basic_consume(prefetch_count=1,
                                    callback=callback, *args, **kwargs)
            return consume_promise

        # if callback:
        #     assert callable(callback)
        #     with self.lock:
        #         consume_promise = self.conn.basic_consume(prefetch_count=1,
        #             callback=callback, *args, **kwargs)
        #         return consume_promise
        # else:
        #     r = AsyncResult()
        #     with self.lock:
        #         consume_promise = self.conn.basic_consume(prefetch_count=1,
        #             callback=lambda p, res: r.set(res), *args, **kwargs)
        #         return consume_promise

        # def do_consume(self, *args, **kwargs):
        #     with self.lock:
        #         # Using basic_consume instead of basic_get as basic_get makes
        #         # only one request and hence needs to constantly poll the
        #         # RabbitMQ server.
        #         #
        #         # basic_consume on the other hand, registers the consumer with
        #         # RabbitMQ which then calls back when there are new messages.
        #         # prefetch_count = 1, ensures that one consumer only works with
        #         # one message at a time
        #         consume_promise = self.conn.basic_consume(prefetch_count=1,
        #                             *args, **kwargs)
        #         if 'callback' in kwargs and kwargs['callback']:
        #             self.conn.loop()
        #         return consume_promise

        # response = None
        # if callback:
        #     assert callable(callback)
        #     gthread = gevent.spawn(do_consume, self, *args,
        #                     callback=callback, **kwargs)
        #     #response = gthread.get()
        # else:
        #     response = do_consume(self, *args, **kwargs)
        # return response

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

    def reject(self, received_result):
        """
        Reject a message received from an AMQP queue.
        """
        return self._run_with_callback(method=self.conn.basic_reject,
                    msg_result=received_result)

    def exchange_declare(self, exchange):
        """
        Declare an exchange synchronously
        """
        return self._run_with_callback(method=self.conn.exchange_declare,
                    exchange=exchange)

    def queue_declare(self, queue):
        """
        Declare a queue synchronously
        """
        return self._run_with_callback(method=self.conn.queue_declare,
                    queue=queue)

    def queue_bind(self, *args, **kwargs):
        """
        Bind a queue to an exchange synchronously
        """
        return self._run_with_callback(method=self.conn.queue_bind,
                    *args, **kwargs)

    def exchange_delete(self, exchange):
        """
        Delete an exchange synchronously
        """
        return self._run_with_callback(method=self.conn.exchange_delete,
                    exchange=exchange)

    def queue_delete(self, queue):
        """
        Delete a queue synchronously
        """
        return self._run_with_callback(method=self.conn.queue_delete,
                    queue=queue)

    def cancel(self, consume_promise):
        """
        Cancel a consumer from an AMQP queue.
        """
        return self._run_with_callback(method=self.conn.basic_cancel,
                    consume_promise=consume_promise)

    def close(self):
        print "Signalling loop to stop"
        self.conn._loop_break = True
        self.greenlet.join()
        self.conn.close()

    def loop(self):
        '''
        Wait for any promise. Block forever until loop_break is called.

        This function overrides identical from puka.Connection to:
        - set timeout on select.
        - remove timeout on function execution - use gevent.Timeout instead.
        '''
        conn = self.conn

        td = 0.2
        conn._loop_break = False

        while True:
            conn.run_any_callbacks()

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
        print '__del__ called'
        self.close()
