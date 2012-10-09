"""An example Nucleon application."""

__version__ = '0.0.1'

# from nucleon.config import settings
from nucleon.signals import on_initialise

from nucleon.framework import Application
app = Application()

import os
import time
import random
import logging

logformat = logging.Formatter('%(asctime)s %(levelname)s logger %(message)s')
logfile = os.path.join(os.path.dirname(__file__), 'test.log')
app_log = logging.getLogger('events')


@on_initialise
def configure_logging():
    """Configure logging when the app starts"""
    log_handler = logging.FileHandler(logfile)
    log_handler.setFormatter(logformat)
    app_log.addHandler(log_handler)
    app_log.setLevel(logging.INFO)


def status(request):
    return {
        'pid': os.getpid(),
        'pgrp': os.getpgrp(),
    }


@app.view('/')
def log_visit(request):
    """A Test View that does a lot of logging"""
    LOGLINE = 'PID: %d. A quick brown fox jumped over the lazy dog' % os.getpid()
    app_log.info(LOGLINE)

    s = time.time()
    while time.time() - s < 0.01:
        """Busy loop to slow gevent's ability to accept().

        Any gevent-patched blocking function will allow the server to
        immediately call accept() again. So we busy-wait instead of blocking.

        Note that this trick wouldn't work if the server accepted() again
        before starting the request handler greenlet, but gevent doesn't appear
        to work like that at this time.

        """
    return status(request)
