#!/usr/bin/python

"""Entry point to a Nucleon application.

This module contains functions for patching gevent and psycopg2, and starting
the Nucleon server.

"""
import os

#This is required for gevent v1.0b2
os.environ['GEVENT_RESOLVER'] = 'ares'

import gevent
import signal
import pwd
import grp
import sys
import logging
import struct
import socket as python_socket

from gevent.socket import socket as gevent_socket
from gevent.pywsgi import WSGIServer

from .signals import on_initialise, on_start, Signal
from .config import settings


HALT_TIMEOUT = 10
logger = logging.getLogger(__name__)


def daemonise_nucleon(pidfile, uid_name, gid_name):
    """Perform the steps necessary to daemonise"""
    # if uid_name is not supplied, use the current user/group
    if not uid_name:
        uid_name = pwd.getpwuid(os.getuid()).pw_name
        gid_name = grp.getgrgid(os.getgid()).gr_name

    # Get the uid/gid from the supplied name
    running_uid = pwd.getpwnam(uid_name).pw_uid
    if not gid_name:
        running_gid = pwd.getpwnam(uid_name).pw_gid
        gid_name = grp.getgrgid(running_gid).gr_name
    else:
        running_gid = grp.getgrnam(gid_name).gr_gid

    # fork for the first time
    try:
        forked_pid = os.fork()
        if forked_pid != 0:
            os._exit(0)
    except OSError, e:
        logger.error('fork #1 failed: %d (%s)' % (e.errno, e.strerror))
        sys.exit(1)

    # open pidfile handle and set umask before dropping permissions
    pf = None
    if pidfile:
        try:
            # Ensure a very conservative umask
            # 177 = read and write for running user only
            os.umask(0177)
            pf = open(pidfile, 'w')
        except OSError:
            logger.error('Cannot open pidfile')
            sys.exit(1)

    started_euid = os.geteuid()
    if started_euid == 0:
        if running_uid == 0:
            # if trying to run as root, give a warning
            logger.warn('Running daemon as root (not recommended)!')
        else:
            # Need to drop privs after opening log file
            try:
                # Remove group privileges
                os.setgroups([])

                # Try setting the new uid/gid
                os.setgid(running_gid)
                os.setuid(running_uid)
                logger.info('Running as user %s:%s' % (uid_name, gid_name))

            # Maybe there is no nucleon user on the system
            except OSError, e:
                logger.error('Error dropping permissions: %d (%s)' % (e.errno, e.strerror))
                sys.exit(1)
    else:
        # if the current user doesn't have sudo permissions:
        # check if user is same, if not raise error
        if started_euid != running_uid:
            if pf:
                pf.close()
                os.unlink(pidfile)
            logger.error('Need su permissions to change user')
            sys.exit(1)

    # Set the working directory
    os.chdir('/')

    # Make sure we have no session leader
    os.setsid()

    # Fork for the second time
    try:
        forked_pid = os.fork()
        if forked_pid != 0:
            os._exit(0)
    except OSError, e:
        if pf:
            pf.close()
            os.unlink(pidfile)
        logger.error('fork #2 failed: %d (%s)' % (e.errno, e.strerror))
        sys.exit(1)

    # Now we have our long-lived PID, write it to the pidfile
    if pf:
        pf.write(str(os.getpid()))
        pf.close()
        del(pf)

    sys.stdout.flush()
    sys.stderr.flush()

    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+', 0)

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())


def bootstrap_gevent():
    # Patch the standard library to use gevent
    import gevent.monkey
    gevent.monkey.patch_all()

    # Patch psycopg2 to use gevent coroutines instead of blocking
    from nucleon.database import psyco_gevent
    psyco_gevent.make_psycopg_green()


def serve(app, access_log, error_log, host, port,
        user, group, no_daemonise, pidfile):
    """Start the server. Does not return."""
    # create the log directory if it doesn't already exist
    if os.path.dirname(access_log) and\
        not os.path.exists(os.path.dirname(access_log)):
        os.mkdir(os.path.dirname(access_log))

    with open(access_log, 'a+') as f:
        # set up logging
        level = logging.INFO
        # TODO: get logging level from settings

        logging.basicConfig(
            filename=error_log,
            level=level,
            format="%(asctime)s [%(process)s] %(name)s.%(levelname)s: %(message)s",
            )

        # setup a listener socket before dropping permissions
        try:
            listener_socket = gevent_socket()
            listener_socket.bind((host, port))
            listener_socket.listen(5)
        except python_socket.error:
            logger.exception("Can't connect to %s:%s" % (host, port))
            sys.exit(1)

        # create a WSGIServer instance using the listener socket created
        server = WSGIServer(listener_socket, app, log=f)
        logger.info("Listening on: %s:%s" % (host, port))

        try:
            # daemonise and drop permissions
            if not no_daemonise:
                logger.debug('now daemonising')
                daemonise_nucleon(pidfile, user, group)

            logger.info("Listening on: %s:%s" % (host, port))
            logger.info("Configuration used: %s" % settings.environment)

            d = MultiprocessDaemon(webserver_serve, app, server)
            d.at_exit.connect(listener_socket.close)
            d.start()
        finally:
            sys.exit(0)


def log_exception(prefix):
    """Print an exception to the log in a parseable way."""
    import sys
    import traceback
    try:
        class_, e, tb = sys.exc_info()
        indent = ' ' * 4
        tb = traceback.format_tb(tb)
        lines = []
        for l in tb:
            lines.extend(l.rstrip().splitlines())
        tb = indent + ('\n' + indent).join(lines)
        logger.error('%s: %s: %s\n%s' % (
            prefix,
            class_.__name__,
            e,
            tb
        ))
    except Exception:
        logger.error("Error formatting traceback: " + traceback.format_exc())


def webserver_serve(app, server):
    """Serve app with server.

    This sets up process context, including signal handlers, etc,
    and runs until signalled.

    """
    def signal_handler():
        logger.info('Shutting down.')
        app.stop_serving(timeout=HALT_TIMEOUT)
        server.stop()
        logger.info('Stopped.')

    gevent.signal(signal.SIGUSR1, signal_handler)
    gevent.signal(signal.SIGHUP, signal_handler)
    gevent.signal(signal.SIGTERM, signal_handler)

    on_initialise.fire()
    gevent.spawn_later(1, on_start.fire)

    # serve requests
    try:
        server.serve_forever(stop_timeout=5)
    finally:
        app.stop_serving(timeout=HALT_TIMEOUT)


class MultiprocessDaemon(object):
    """A daemon that forks multiple workers and keeps them alive.

    Each worker will perform the callable given in the constructor.

    """
    def __init__(self, worker, *args, **kwargs):
        self.workers = set()
        self.worker = worker
        self.args = args
        self.kwargs = kwargs

        self.at_exit = Signal()

    def start(self, processes=4):
        """Spawn a number of worker process and keep them alive.

        Does not return.

        """
        # gevent.signal() doesn't work - presumably because the master is
        # usually blocked in os.wait()
        signal.signal(signal.SIGUSR1, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        os.setpgid(os.getpid(), 0)  # Create a process group
        try:
            self.keeprunning = True
            for proc in xrange(processes):
                self.spawn_worker()

            while self.workers:
                pid, sig = os.wait()   # Block until a child dies
                if pid in self.workers:
                    self.workers.remove(pid)
                    if not self.keeprunning:
                        # Don't respawn if we're shutting down
                        continue
                    logging.info("Worker process exited. Respawning.")
                    self.spawn_worker()
            self.at_exit.fire()
        except Exception:
            log_exception("Fatal exception in control process")
            sys.exit(1)
        sys.exit(0)

    def stop(self):
        """Stop the daemon and all workers."""
        self.keeprunning = False
        for pid in self.workers:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass

    def spawn_worker(self):
        """Spawn a new worker."""
        pid = os.fork()
        if pid:
            # This is the parent process
            self.workers.add(pid)
            os.setpgid(pid, os.getpid())  # Add child to our process group
        else:
            logger.info("Worker started")
            try:
                self.worker(*self.args, **self.kwargs)
            except Exception:
                log_exception('Fatal exception in worker')
                sys.exit(1)
            except SystemExit:
                pass
            sys.exit(0)

    def signal_handler(self, sig=None, frame=None):
        """Handle a shutdown signal by shutting down the workers."""
        logger.info("Caught signal %d, shutting down workers." % sig)
        self.stop()
