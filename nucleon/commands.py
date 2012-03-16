# Bootstrap gevent before we do anything else
from nucleon.main import bootstrap_gevent
bootstrap_gevent()

import os
import sys
import os.path
import argparse

class Command(object):
    """
    Protocol definition for Commands.

    Class __doc__ is used as help.
    """

    DEFAULTS = {
        'host': '127.0.0.1',
        'port': 8888,
        'access_log': 'access.log',
        'error_log': 'error.log',
        'no_daemonise': False,
        'pidfile': None,
    }

    def __call__(self, namespace):
        raise NotImplemented

    def _configure_parser(self, parser):
        """
        Override to add parser.add_argument(...)
        Default implementation is empty.
        """

    def get_parser(self):
        """
        Returns Parser object with add_help set to False
        and configures using self._configure_parser(parser)

        In case no rule is configured an empty parser is returned
        and is later ignored by argparse.
        """
        parser = argparse.ArgumentParser(add_help=False)
        self._configure_parser(parser)
        return parser


class NewCommand(Command):
    """Create a new nucleon app project"""

    def _configure_parser(self, parser):
        parser.add_argument('destination', type=str,
                help='a destination directory')

    def copy_recursive(self, dest, resource):
        """Recursively copy files to dest from the pkg_resources resource."""
        import posixpath
        from pkg_resources import (resource_listdir, resource_string,
            resource_isdir)

        try:
            os.mkdir(dest)
        except OSError, e:
            sys.exit("Couldn't create directory %s: %s" % (dest, e.strerror))
        for fname in resource_listdir(__name__, resource):
            f = posixpath.join(resource, fname)
            if resource_isdir(__name__, f):
                self.copy_recursive(os.path.join(dest, fname), f)
            else:
                s = resource_string(__name__, f)
                with open(os.path.join(dest, fname), 'w') as out:
                    out.write(s)

    def __call__(self, args):
        dest = args.destination
        self.copy_recursive(dest, 'skel')
        print "Created app", dest


class AppCommand(Command):
    """
    Abstract app command

    handles --configuration argument
    when overriding get_parser(self) method remember to chain
    ArgumentParser(parents=[super(..).get_parser()])

    to use this class, please define subclass that defines
    __call__(self, args) method
    """

    def _configure_parser(self, parser):
        parser.add_argument('-c', '--configuration', type=str,
            metavar='CONFIG',
            help='Configuration section in app.cfg file.'
                ' Overrides NUCLEON_CONFIGURATION environment variable.')

    def get_app(self, args):
        from nucleon.loader import get_app
        app = get_app()
        if args and hasattr(args, 'configuration') \
            and args.configuration is not None:
            app.environment = args.configuration
        return app


class StartCommand(AppCommand):
    """Start the app located in the current directory"""
    # Import app from the current directory

    def _configure_parser(self, parser):
        super(StartCommand, self)._configure_parser(parser)
        parser.add_argument('--host', type=str, default=self.DEFAULTS['host'],
            help='ip/hostname of interface where server will bind'
                ' (default: %(default)s)')
        parser.add_argument('--port', type=int, default=self.DEFAULTS['port'],
            help='port where server will bind (default: %(default)s)')
        parser.add_argument('--user', type=str, default='',
            help='user the server daemon will run under')
        parser.add_argument('--group', type=str, default='',
            help='group the server daemon will run under')
        parser.add_argument('--access_log', type=str,
            default=self.DEFAULTS['access_log'],
            help='requests log in format similar to access_log'
                ' (default: %(default)s)')
        parser.add_argument('--error_log', type=str,
            default=self.DEFAULTS['error_log'],
            help='errors and system notifications log to this file'
                ' (default: %(default)s)')
        parser.add_argument('--pidfile', type=str,
            default=self.DEFAULTS['pidfile'],
            help='use the filename supplied to store the PID'
                ' (default: %(default)s)')
        parser.add_argument('--no_daemonise',
            default=self.DEFAULTS['no_daemonise'], action="store_true",
            help="do not daemonise the nucleon app (default: %(default)s)")

    def __call__(self, args=None):
        from nucleon.main import serve
        def param(name):
            """Get an argument if passed or else get it from defaults""" 
            if args and hasattr(args, name):
                return getattr(args, name)
            else: 
                return self.DEFAULTS[name]

        # Setup the defaults
        access_log = param('access_log')
        error_log = param('error_log')
        host = param('host')
        port = param('port')
        user = param('user')
        group = param('group')
        pidfile = param('pidfile')
        no_daemonise = param('no_daemonise')

        app = self.get_app(args)

        # Start the nucleon app with teh specified parameters
        serve(app, access_log=access_log, error_log=error_log,
            host=host, port=port, user=user, group=group,
            no_daemonise=no_daemonise, pidfile=pidfile)


class SyncdbCommand(AppCommand):
    """Create tables that do not exist."""

    def __call__(self, args):
        app = self.get_app(args)
        sqlscript = app.load_sql('database.sql')
        db = app.get_database()
        sqlscript = sqlscript.make_sync_script(db)
        for response in sqlscript.execute(db):
            print response


class ResetdbCommand(AppCommand):
    """Fully re-initialise the database."""

    def __call__(self, args):
        app = self.get_app(args)
        sqlscript = app.load_sql('database.sql')
        sqlscript = sqlscript.make_reinitialize_script()
        db = app.get_database()

        for response in sqlscript.execute(db):
            print response


COMMANDS = {
    'new': NewCommand,
    'start': StartCommand,
    'syncdb': SyncdbCommand,
    'resetdb': ResetdbCommand,
}


def make_function(name, command_class):
    """Make a callable function from a command class.

    The resulting function should be called with functions matching the
    commandline arguments. Thus if the commandline call was

    $ nucleon start --port 8080

    then the corresponding function call would be

    >>> start('--port', '8080')

    """
    def _call_command(*args):
        cmd = command_class()
        parser = cmd.get_parser()
        arguments = parser.parse_args(args)
        cmd(arguments)
    _call_command.__doc__ == command_class.__doc__
    _call_command.__name__ == name
    return _call_command


# create commands as global variables
module = sys.modules[__name__]
for command, command_class in COMMANDS.iteritems():
    setattr(module, command, make_function(command, command_class))


def main():
    """Entry point for the nucleon commandline."""
    from nucleon import __version__
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + __version__)
    subparsers = parser.add_subparsers(metavar='command')
    # let's register all specified COMMANDS
    for (name, command_class) in COMMANDS.iteritems():
        command = command_class()
        parent_parser = command.get_parser()
        sub_parser = subparsers.add_parser(name, parents=[parent_parser],
                                            help=command.__doc__)
        sub_parser.set_defaults(func=command)

    args = parser.parse_args()
    args.func(args)     # executes selected command
