#!/usr/bin/env python

import gevent.monkey
gevent.monkey.patch_all()
from gevent.queue import Queue
import puka


"""
1. sending
1.1 let there be a wrapper for sending a message
- sync
- async

1.2 let there be a greenlet waiting for async responses and a mechanism to react to them


2. receiving
2.1 let there be a greenlet waiting for messages and a way to register async handlers for them


3. let there be a way to read configuration from nucleon conf
AMQP_URL = "amqp://user:pass@hostname:port/vhost"
AMQP_URL = "amqp:///"


4. let developer decide on queues structure - out of nucleon conf
it is specific for amqp that queues,exchanges are runtime defined



"""

#TODO: test if connections won't timeout



# END POOL




def initmq():
    AMQP_URL = "amgp:///"



class MQ:
    def __init__(self):
        self.client = puka.Client("amqp:///")
        self.event_loop = gevent.spawn(client.loop)
        self.lock = gevent.RLock()

    def basic_consume(self, *args, **kwargs):
        q = gevent.coros.Queue()
        with self.lock:
            self.client.basic_consume(*args, callback=lambda resp: q.put(resp), **kwargs)
        return q.get()


def update_customer():
    conn.tpc_prepare()
    amqp.basic_publish()
    conn.tpc_commit()


def update_something():
    promise = amqp.basic_publish(async=True)
    promise2 = amqp.basic_publish(async=True)
    res1, res2 = amqp.wait_all(promise, promise2)


def listen_for_x_events(amqp):
    while True:
        try:
            msg = amqp.basic_consume()
            print msg
            # do something with msg
        except:
            continue


#@app.on_start
#def start_listener_thread():
#    gevent.spawn(listen_on_queue_x, app.get_queue())
#    gevent.spawn(listen_on_queue_y, app.get_queue())


def async_init_listener():
    gevent.spawn(init_listener)

def init_listener():
    client = puka.Client(AMQP_CONSUMER_URL)
    promise = client.connect()
    client.wait(promise)



class Application():
    config = {
        'AMQP_LISTEN_URL':'amqp:///',
        'AMQP_LISTEN_POOL_SIZE':10,
        'AMQP_PUBLISH_URL':'amqp:///',
        'AMQP_PUBLISH_POOL_SIZE':10,
    }
    _amqp_publish_connection = None
    _amqp_listen_connection = None
    on_start_funcs = []

    def __init__(self):
        pass

    def run(self):
        for func in self.on_start_funcs:
            func()

    def get_amqp_connection(self):
        """
        we may want to introduce pooling
        """
        if not self._amqp_connection:
            self._amqp_connection = puka.Client(self.config['AMQP_URL'])
        return self._amqp_connection

    def on_start(self,func):
        self.on_start_funcs.append(func)
        def f(*args, **kwargs):
            func(*args, **kwargs)
        return f

app = Application()



app.run()
