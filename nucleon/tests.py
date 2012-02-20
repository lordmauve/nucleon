from nucleon.loader import get_app
from nucleon.signals import on_initialise, on_start
from webtest import TestApp


def get_test_app(relpath=None):
    """Build a test version of the app.

    If given, relpath is the path of a file within the app's directories; this
    will be used to find the correct app to import.
    """
    from nucleon.config import settings

    app = get_app(relpath)
    settings._set_environment('test')
    on_initialise.fire()
    on_start.fire()
    return TestApp(app)
