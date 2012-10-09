#!/usr/bin/python

"""Entry point to a Nucleon application.

This module contains functions for patching gevent and psycopg2, and starting
the Nucleon server.

"""
import os

#This is required for gevent v1.0b2
os.environ['GEVENT_RESOLVER'] = 'ares'

import errno
import gevent
import signal
import pwd
import grp
import sys
import logging
import traceback
import struct
import socket as python_socket

from gevent.pool import Pool
from gevent.socket import socket as gevent_socket
from gevent.pywsgi import WSGIServer

import gevent.coros

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
    with open(access_log, 'a+') as access_file:
        if no_daemonise:
            # Log to the console when not daemonised
            error_log = None
            level = logging.DEBUG
        else:
            # TODO: get logging level from settings
            level = logging.INFO

        # set up logging
        logging.basicConfig(
            filename=error_log,
            level=level,
            format="%(asctime)s [%(process)s] %(name)s.%(levelname)s: %(message)s",
        )

        # setup a listener socket before dropping permissions
        try:
            listener_socket = gevent_socket()
            # Make the address reusable
            listener_socket.setsockopt(
                python_socket.SOL_SOCKET, python_socket.SO_REUSEADDR, 1
            )
            listener_socket.bind((host, port))
            listener_socket.listen(5)
        except python_socket.error as e:
            logger.error("Can't bind socket: %s", e)
            sys.exit(1)

        logger.info("Listening on: %s:%s" % (host, port))
        logger.info("Configuration used: %s" % settings.environment)

        try:
            # daemonise and drop permissions
            if not no_daemonise:
                logger.debug('now daemonising')
                daemonise_nucleon(pidfile, user, group)

            d = MultiprocessDaemon(webserver_serve, access_file, app, listener_socket)
            d.at_exit.connect(listener_socket.close)
            d.start()
        finally:
            sys.exit(0)


def log_exception(prefix):
    """Print an exception to the log in a parseable way."""
    import sys
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


def webserver_serve(app, listener_socket, logfile):
    """Serve app on listener_socket provided.

    This sets up process context, including signal handlers, etc,
    and runs until signalled.

    """
    # create a WSGIServer instance using the listener socket created
    server = WSGIServer(listener_socket, app, log=logfile)
    server.set_spawn(Pool())  # Make WSGIServer manage worker greenlets

    def signal_handler():
        # logger.debug('webserver_serve.signal_handler: Worker caught signal. Shutting down.')
        app.stop_serving(timeout=HALT_TIMEOUT)
        server.stop()

    gevent.signal(signal.SIGUSR1, signal_handler)
    gevent.signal(signal.SIGINT, signal_handler)
    gevent.signal(signal.SIGHUP, signal_handler)
    gevent.signal(signal.SIGTERM, signal_handler)

    on_initialise.fire()
    gevent.spawn_later(1, on_start.fire)

    # serve requests
    try:
        server.serve_forever(stop_timeout=5)
    finally:
        server.close()
        logger.debug('webserver_serve: finished serving')


class GreenWriter(object):
    """Class that writes to a file descriptor without blocking all greenlets"""
    def __init__(self, fd):
        self.fd = fd

    def write(self, data):
        wrote = 0
        len_data = len(data)
        while wrote < len_data:
            gevent.socket.wait_write(self.fd)
            wrote += os.write(self.fd, data[wrote:])


class MultiprocessDaemon(object):
    """A daemon that forks multiple workers and keeps them alive.

    Each worker will perform the callable given in the constructor.

    """
    def __init__(self, worker, access_file, *args, **kwargs):
        self.workers = set()
        self.worker = worker
        self.access_file = access_file
        self.args = args
        self.kwargs = kwargs

        self.in_buff = ''
        self.logger_threads = []
        self.at_exit = Signal()
        self.stopping = gevent.event.Event()
        self.access_file_lock = gevent.coros.RLock()

    def start(self, processes=4):
        """Spawn a number of worker process and keep them alive.

        Does not return.

        """
        gevent.signal(signal.SIGCHLD, self.on_worker_exit, 'SIGCHLD')
        gevent.signal(signal.SIGUSR1, self.signal_handler, 'SIGUSR1')
        gevent.signal(signal.SIGINT, self.signal_handler, 'SIGINT')
        gevent.signal(signal.SIGTERM, self.signal_handler, 'SIGTERM')

        os.setpgid(os.getpid(), 0)  # Create a process group
        try:
            # logger.debug('MPD.start: spawning processes')
            self.keeprunning = True
            self.is_child_process = False

            for proc in xrange(processes):
                self.spawn_worker()

            # Read logs from the workers over their log pipe
            logger.debug('MPD.start: now waiting in the master thread')
            self.stopping.wait()

            self.at_exit.fire()
            logger.info('Exiting.')
        except Exception, e:
            log_exception("Fatal exception in control process")
            sys.exit(1)
        sys.exit(0)

    def on_worker_exit(self, sig=None, frame=None):
        assert sig == 'SIGCHLD'

        # We need to make sure that the main thread is not calling os.wait()
        # os.wait() calls os.waitpid(pid). If the process exited while in this thread
        # the main thread's os.waitpid(pid) will raise "OSError: no child processes"
        # (because the process ended in another thread)
        #
        # So we are using this lock to make sure only one thread executes os.wait()
        acquired = self._wait_lock.acquire(False)
        if not acquired:
            return

        try:
            pid, sig = os.wait()   # Block until a child dies
            # logger.debug('MPD.on_worker_exit: finished os.wait(). workers: %d' % len(self.workers))

            if pid in self.workers:
                self.workers.remove(pid)
                if not self.keeprunning:
                    # Don't respawn if we're shutting down
                    return
                logger.debug("MPD.on_worker_exit: Worker process exited. Respawning.")
                self.spawn_worker()

        except OSError as e:
            return
        finally:
            self._wait_lock.release()

    def stop(self):
        """Stop the daemon and all workers."""
        self.keeprunning = False
        for pid in self.workers:
            try:
                os.kill(pid, signal.SIGTERM)
                # logger.debug('send SIGTERM signal to %d' % (int(pid)))
            except OSError:
                logger.debug('OSError raised when killing process %d: %s' % (int(pid)), traceback.format_exc())
                pass
        # logger.debug('sent os.kill. joining %d logger_threads' % len(self.logger_threads))
        gevent.joinall(self.logger_threads)
        # logger.debug('MPD.stop: joined all logger threads')
        if not self.is_child_process:
            # logger.debug('MPD.stop: closing access file handle and setting stopping event')
            self.access_file.close()
            self.stopping.set()

    def logger(self, rfd):
        # logger.debug('MPD.logger(%s): logger started. rfd: %s' % (str(gevent.getcurrent()), str(rfd)))
        buf = ''
        try:
            while True:
                gevent.socket.wait_read(rfd)

                chunk = os.read(rfd, 4096)
                buf += chunk
                if not buf:
                    break

                try:
                    line, buf = buf.rsplit('\n', 1)
                    # logger.debug('MPD.logger(%s): chunk = %s, line = %s, buf = %s' % (str(gevent.getcurrent()), chunk, line, buf))
                except ValueError:
                    pass
                else:
                    if line:
                        line += '\n'
                        with self.access_file_lock:
                            # logger.debug('MPD.logger(%s): got file lock.')
                            self.access_file.write(line)
        finally:
            os.close(rfd)

    def spawn_worker(self):
        """Spawn a new worker."""
        # Enable Gevent's libev child watcher to reap children (catch SIGCHLD)
        gevent.get_hub().loop.install_sigchld()

        rfd, wfd = os.pipe()
        pid = os.fork()
        if pid:
            # This is the parent process
            os.close(wfd)
            self.logger_threads.append(gevent.spawn(self.logger, rfd))

            self.workers.add(pid)
            os.setpgid(pid, os.getpid())  # Add child to our process group
            self._wait_lock = gevent.coros.RLock()
        else:
            gevent.killall(self.logger_threads)
            self.logger_threads = []
            self.workers = []
            os.close(rfd)
            self.is_child_process = True
            self._wait_lock = None

            w = GreenWriter(wfd)
            self.kwargs['logfile'] = w

            # logger.debug("MPD.spawn_worker: Worker started. kwargs=%s" % self.kwargs)
            try:
                self.worker(*self.args, **self.kwargs)
            except Exception:
                log_exception('Fatal exception in worker')
                sys.exit(1)
            except SystemExit:
                pass
            # logger.debug('MPD.spawn_worker: worker finished')
            sys.exit(0)

    def signal_handler(self, sig=None, frame=None):
        """Handle a shutdown signal by shutting down the workers."""
        logger.info("MPD.signal_handler: Caught signal %s, shutting down." % str(sig))
        self.stop()
