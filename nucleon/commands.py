# Bootstrap gevent before we do anything else
from nucleon.main import bootstrap_gevent
bootstrap_gevent()


def start():
    """Start the app located in the current directory."""
    # Import app from the current directory
    from nucleon.loader import get_app
    from nucleon.main import serve
    app = get_app()
    serve(app)


COMMANDS = {
    'start': start,
}


def main():
    """Entry point for the nucleon commandline."""
    import sys
    cmd = sys.argv[1]
    COMMANDS[cmd]()

