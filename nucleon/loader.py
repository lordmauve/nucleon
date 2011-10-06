import os
import imp
import sys


def get_app(relpath=None):
    """Search for an load an application.

    If relpath is given, this is the path to search from (the default is the
    current working directory.)

    """
    if relpath is None:
        relpath = os.getcwd()
    elif not os.path.isdir(relpath):
        relpath = os.path.dirname(relpath)

    path = os.path.abspath(relpath)

    while path != '/':
        try:
            module = imp.find_module('app', [path])
        except ImportError:
            path = os.path.abspath(os.path.join(path, '..'))
        else:
            sys.path.insert(0, path)
            app = imp.load_module('app', *module)
            return app.app

    raise ImportError("Couldn't find Nucleon app to import")
