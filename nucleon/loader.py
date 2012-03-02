import sys
import os
import os.path
import imp

from nucleon.config import settings, SETTINGS_FILENAME

app = None

def get_app(relpath=None):
    """Search for an load an application.

    If relpath is given, this is the path to search from (the default is the
    current working directory.)

    """
    global app
    if app:
        return app

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
            app = imp.load_module('app', *module).app
            configfile = os.path.join(path, SETTINGS_FILENAME)
            settings._load(filename=configfile)
            app._path = path
            return app

    raise ImportError("Couldn't find Nucleon app to import")
