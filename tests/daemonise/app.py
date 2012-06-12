import os
import time

from nucleon.framework import Application
app = Application()


@app.view('/status')
def status(request):
    return {
        'pid': os.getpid(),
        'pgrp': os.getpgrp(),
    }


@app.view('/slow-status')
def slow_status(request):
    s = time.time()
    while time.time() - s < 0.2:
        """Busy loop to slow gevent's ability to accept().

        Any gevent-patched blocking function will allow the server to
        immediately call accept() again. So we busy-wait instead of blocking.

        Note that this trick wouldn't work if the server accepted() again
        before starting the request handler greenlet, but gevent doesn't appear
        to work like that at this time.

        """

    return status(request)
