# Bootstrap gevent before we do anything else
from nucleon.main import bootstrap_gevent
bootstrap_gevent()

import os
import os.path
import argparse


class Command(object):
    """
    Protocol definition for Commands.

    Class __doc__ is used as help.
    """

    def __call__(self, namespace):
        raise NotImplemented

    def _configure_parser(self, parser):
        """
        Override to add parser.add_argument(...)
        Default implementation is empty.
        """

    def get_parser(self):
        """
        Returns Parser object with add_help set to False and configured using self._configure_parser(parser)

        In case no rule is configured an empty parser is returned and is later ignored by argparse.
        """
        parser = argparse.ArgumentParser(add_help=False)
        self._configure_parser(parser)
        return parser


class NewCommand(Command):
    """Start a new nucleon app"""
    # find skel directory

    def _configure_parser(self, parser):
        parser.add_argument('destination', type=str, help='a destination directory')

    def __call__(self, args):
        import shutil

        skel = os.path.join(os.path.dirname(__file__), 'skel')
        dest = args.destination
        shutil.copytree(skel, dest)
        print "Created app", dest


class AppCommand(Command):
    """
    Abstract app command

    handles --configuration argument
    when overriding get_parser(self) method remember to chain ArgumentParser(parents=[super(..).get_parser()])

    to use this class, please define subclass that defines __call__(self, args) method
    """

    def _configure_parser(self, parser):
        parser.add_argument('-c', '--configuration', type=str,  metavar='CONFIG',
                               help='Configuration section in app.cfg file. Overrides NUCLEON_CONFIGURATION environment variable.')

    def get_app(self, args):
        from nucleon.loader import get_app
        app = get_app()
        if args.configuration is not None:
            app.environment = args.configuration
        return app


class StartCommand(AppCommand):
    """Start the app located in the current directory"""
    # Import app from the current directory

    def _configure_parser(self, parser):
        super(StartCommand,self)._configure_parser(parser)
        parser.add_argument('--host', type=str, default='0.0.0.0',
                            help='ip/hostname of interface where server will bind (default: %(default)s)')
        parser.add_argument('--port', type=int, default=8888,
                            help='port where server will bind (default: %(default)s)')
        parser.add_argument('--logfile', type=str, default='nucleon.log',
                            help='requests log in format similar to access_log (default: %(default)s)')

    def __call__(self, args):
        from nucleon.main import serve
        app = self.get_app(args)
        serve(app,logfile=args.logfile,host=args.host,port=args.port)


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


def main():
    """Entry point for the nucleon commandline."""
    from nucleon import __version__
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    subparsers = parser.add_subparsers(metavar='command')
    # let's register all specified COMMANDS
    for (name, command_class) in COMMANDS.iteritems():
        command = command_class()
        parent_parser = command.get_parser()
        sub_parser = subparsers.add_parser(name, parents=[parent_parser], help=command.__doc__)
        sub_parser.set_defaults(func=command)

    args = parser.parse_args()
    args.func(args) # executes selected command

