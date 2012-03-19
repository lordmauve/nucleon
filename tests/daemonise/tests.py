from nose.tools import eq_, with_setup
import sys
import os
import os.path
import urllib2
import signal
from pwd import getpwuid
from grp import getgrgid
from time import sleep

from mock import Mock

current_dir = os.path.abspath(os.path.dirname(__file__))
pidfile = os.path.join(current_dir, 'nucleon.pid')
access_log = os.path.join(current_dir, 'access.log')
error_log = os.path.join(current_dir, 'error.log')


def kill_from_pidfile(pidfile):
    """Kill a process whose pid is in pidfile.

    Also waits for up to 10s for the process to stop, by polling /proc.
    """
    with open(pidfile, 'r') as pdfh:
        pid = pdfh.read().strip()

    if pid and os.path.exists('/proc/%s' % pid):
        os.kill(int(pid), 2)

        for i in xrange(10):
            if not os.path.exists('/proc/%s' % pid):
                break
            sleep(1)
        else:
            os.kill(int(pid), 9)


def setup():
    """Ensure pidfile does not exist. If it does, kill the process"""
    if os.path.exists(pidfile):
        kill_from_pidfile(pidfile)
        os.unlink(pidfile)
#    if os.path.exists(error_log):
#        os.unlink(error_log)


def teardown():
    """At the end of tests, try and kill nucleon and cleanup"""
    if os.path.exists(pidfile):
        kill_from_pidfile(pidfile)

        # Ensure pidfile does not exist
        os.remove(pidfile)
        assert not os.path.exists(pidfile)

        # Lastly, test daemon is not running
#        if pid:
#            eq_(not os.path.exists('/proc/%s' % pid), True)


def check_daemon(pid, port='8888'):
    """Check that the given process is running as a daemon"""
    # test daemon is running
    assert os.path.exists('/proc/%s' % pid)

    # Test parent process is init
    procstat = open("/proc/%s/stat" % pid).read()
    ppid = procstat.split(' ')[3]
    assert ppid == '1'

    # Make sure nucleon is running in the right working directory

    # Ensure standard file descriptors are disposed of
    for std_fd in ['0', '1', '2']:
        fd = os.path.exists("/proc/%s/fd/%s" % (pid, std_fd))
        # It is ok if the file descriptor is closed
        if fd is False:
            assert True
        # It is OK if the file descriptors
        else:
            fd = os.readlink("/proc/%s/fd/%s" % (pid, std_fd))
            assert fd == os.devnull

    status = None
    try:
        out = urllib2.urlopen('http://localhost:%s/' % port).read()
    except urllib2.HTTPError, e:
        status = e.code
    assert status == 404


def wait_for_pidfile():
    """Waits for the pidfile to be created for a maximum of 10 secs"""
    total_wait = 0
    while True:
        sleep(1)
        total_wait += 1
        assert total_wait < 10, "pidfile (%s) wasn't written after 10s" % pidfile
        try:
            with open(pidfile, 'r') as f:
                if f.read().strip():
                    break
        except OSError:
            continue


def kill_daemon(pid):
    """Kill a running daemon and wait for it to die"""
    # send kill signal
    os.kill(int(pid), signal.SIGTERM)
    # wait till the process ends
    total_wait = 0
    while os.path.exists('/proc/%s' % pid):
        sleep(0.2)
        total_wait += 0.2
        if total_wait >= 10:
            break
    assert total_wait < 10


arguments = {
    '--access_log': access_log,
    '--error_log': error_log,
    '--pidfile': pidfile,
    '--port': '8888',
    '--host': '127.0.0.1',
    '--user': '',
    '--group': '',
    # '--no_daemonise': False,
}


def args_list(args_dict):
    """Generate a list of arguments given a dictionary"""
    l = []
    for k, v in args_dict.items():
        l += [k, v]
    return l


@with_setup(setup, teardown)
def test_app_daemonise():
    """Test that the app daemonises correctly"""

    # spawn nucleon and wait a moment for app to come up
    os.system("nucleon start --port=7001 --pidfile=%s --access_log=%s --error_log=%s"\
            % (pidfile, access_log, error_log))

    # wait for pidfile to be written
    wait_for_pidfile()

    # test pidfile contents
    pid = open(pidfile).read()
    assert int(pid)

    # check that the daemon is running
    check_daemon(pid, port=7001)

    uid_name = getpwuid(os.getuid()).pw_name
    gid_name = getgrgid(os.getgid()).gr_name

    # Make sure we are running as the current user
    proc = '/proc/%s' % pid
    assert getpwuid(os.stat(proc).st_uid).pw_name == uid_name
    assert getgrgid(os.stat(proc).st_gid).gr_name == gid_name

    # test nucleon stops
    kill_daemon(pid)


@with_setup(setup, teardown)
def test_mock_root_change_user():
    """Test that daemonisation works correctly when started as root but run as different user"""
    # fork nucleon in a different process
    fork_pid = os.fork()

    args = arguments.copy()
    args.update({
        '--port': '7002',
    })

    if fork_pid == 0:
        try:
            # child process to test daemonise
            # mock the os library to return true when asked for root privileges
            os.geteuid = Mock(return_value=0)
            os.setuid = Mock(return_value=True)
            os.setgid = Mock(return_value=True)
            os.setgroups = Mock(return_value=True)

            # we create the access and error log in the current directory
            # as the test process doesn't have access rights to /var/log, etc
            args = args_list(args)

            import nucleon.commands
            nucleon.commands.start(*args)
        finally:
            os._exit(0)
    else:
        # parent test process
        # wait for child process to finish
        os.waitpid(fork_pid, 0)

        # wait for pidfile to be written
        wait_for_pidfile()

        # test pidfile contents
        pid = open(pidfile).read()
        assert int(pid)

        # check that the daemon is running
        check_daemon(pid, port=7002)

        # kill daemon
        kill_daemon(pid)

        # read error log to check output
        assert os.path.exists(error_log)
        success_message = False
        with open(error_log, 'r') as erl:
            for line in erl:
                if 'Running as user' in line:
                    success_message = True
                    break
        assert success_message


@with_setup(setup, teardown)
def test_mock_root_running_as_root():
    """Test that daemonisation works correctly when started as root and run as root"""
    # fork nucleon in a different process
    fork_pid = os.fork()
    if fork_pid == 0:
        try:
            # child process to test daemonise
            # mock the os library to return true when asked for root privileges
            os.geteuid = Mock(return_value=0)
            os.setuid = Mock(return_value=True)
            os.setgid = Mock(return_value=True)
            os.setgroups = Mock(return_value=True)

            # we create the access and error log in the current directory
            # as the test process doesn't have access rights to /var/log, etc
            import copy
            args = copy.deepcopy(arguments)
            args['--user'] = 'root'
            args['--group'] = 'root'
            args['--port'] = '7003'
            args = args_list(args)

            import nucleon.commands
            nucleon.commands.start(*args)
        finally:
            os._exit(0)
    else:
        # parent test process
        # wait for child process to finish
        os.waitpid(fork_pid, 0)

        # wait for pidfile to be written
        wait_for_pidfile()

        # test pidfile contents
        pid = open(pidfile).read()
        assert int(pid)

        # check that the daemon is running
        check_daemon(pid, port=7003)
        # kill daemon
        kill_daemon(pid)

        # read error log to check output
        assert os.path.exists(error_log)
        warning_message = False
        with open(error_log, 'r') as erl:
            for line in erl:
                if 'Running daemon as root (not recommended)' in line:
                    warning_message = True
                    break
        assert warning_message


@with_setup(setup, teardown)
def test_daemonise_not_root_change_user():
    """Test that we can't daemonise as a different user when we're not root"""
    # fork nucleon in a different process
    fork_pid = os.fork()
    if fork_pid == 0:
        try:
            # child process to test daemonise
            import copy
            args = copy.deepcopy(arguments)
            args['--user'] = 'nobody'
            args['--group'] = 'nogroup'
            args['--port'] = '7004'
            args = args_list(args)

            import nucleon.commands
            nucleon.commands.start(*args)
        finally:
            os._exit(0)
    else:
        # parent test process
        # wait for child process to finish
        os.waitpid(fork_pid, 0)
        # wait for the fork #1 to raise error
        sleep(1)

        # test pidfile was not created
        assert not os.path.exists(pidfile)

        # read error log to check output
        assert os.path.exists(error_log)
        error_message = False
        with open(error_log, 'r') as erl:
            for line in erl:
                if 'Need su permissions to change user' in line:
                    error_message = True
                    break
        assert error_message
