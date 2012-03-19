#!/usr/bin/python

"""Entry point to a Nucleon application.

This module contains functions for patching gevent and psycopg2, and starting
the Nucleon server.

"""

import gevent

HALT_TIMEOUT = 10

import os
import pwd
import grp
import sys
import logging
import socket as python_socket

logger = None


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

    sys.stdout.flush()
    sys.stderr.flush()

    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+', 0)

    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def finish_serving(app, server):
    logger.info("Shutting down server...")
    app.stop_serving(timeout=HALT_TIMEOUT)
    server.stop()
    logger.info("Shutdown complete!")

def register_signal(app, server, pidfile):
    import signal

    def signal_handler():
        logger.info('Signal raised')
        finish_serving(app, server)
    gevent.signal(signal.SIGUSR1, signal_handler)
    gevent.signal(signal.SIGTERM, signal_handler)


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
    global logger
    from gevent.pywsgi import WSGIServer
    from gevent.socket import socket as gevent_socket
    from nucleon.signals import on_initialise, on_start
    from nucleon.config import settings

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
            format="%(asctime)s:%(levelname)s:%(name)s:%(message)s",
            )
        logger = logging.getLogger(__name__)
        logger.info('setup logging for pid: ' + str(os.getpid()))

        # setup a listener socket before dropping permissions
        try:
            listener_socket = gevent_socket()
            # listener_socket.setsockopt(python_socket.SOL_SOCKET, python_socket.SO_REUSEADDR, 1)

            # set the listener socket to not linger after it is closed
            # by all processes
            import struct
            listener_socket.setsockopt(python_socket.SOL_SOCKET,
                python_socket.SO_LINGER, struct.pack('ii', 1, 0))

            listener_socket.bind((host, port))
            listener_socket.listen(2)
        except python_socket.error:
            logger.exception("Can't connect to %s:%s" % (host, port))
            sys.exit(1)

        # create a WSGIServer instance using the listener socket created
        server = WSGIServer(listener_socket, app, log=f)

        on_initialise.fire()

        try:
            # daemonise and drop permissions
            if not no_daemonise:
                logger.debug('now daemonising')
                daemonise_nucleon(pidfile, user, group)

            # register signals on the newly created child process
            register_signal(app, server, pidfile)

            logger.info("Daemon started (pid: %s)" % str(os.getpid()))
            logger.info("Listening on: %s:%s" % (host, port))
            logger.info("Configuration used: %s" % settings.environment)

            gevent.spawn_later(1, on_start.fire)

            # serve requests
            try:
                server.serve_forever(stop_timeout=5)
            except:
                app.stop_serving(timeout=HALT_TIMEOUT)
                logger.exception('FATAL: Exception raised when serving')
            finally:
                logger.info('Finished serving. Now closing socket in pid: ' + str(os.getpid()))
                listener_socket.close()
                sys.exit(0)
        finally:
            sys.exit(0)
