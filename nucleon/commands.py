# Bootstrap gevent before we do anything else
from nucleon.main import bootstrap_gevent
bootstrap_gevent()

import os
import os.path


def new(args):
    # find skel directory
    skel = os.path.join(os.path.dirname(__file__), 'skel')
    import shutil
    dest = args[1]
    shutil.copytree(skel, dest)
    print "Created app", dest


def start(args):
    """Start the app located in the current directory."""
    # Import app from the current directory
    from nucleon.loader import get_app
    from nucleon.main import serve
    app = get_app()
    serve(app)


def help(args):
    """Show the command help."""
    for cmd, func in COMMANDS.items():
        if cmd.startswith('-'):
            continue
        print "{0:12} {1}".format(cmd, func.__doc__)


COMMANDS = {
    'new': new,
    'start': start,
    '-h': help,
    '--help': help,
    'help': help,
}


def main():
    """Entry point for the nucleon commandline."""
    import sys

    try:
        cmd = sys.argv[1]
    except IndexError:
        help([])
        return

    COMMANDS[cmd](sys.argv[1:])

