from nucleon.loader import get_app
from webtest import TestApp


def get_test_app(relpath=None):
    """Build a test version of the app.

    If given, relpath is the path of a file within the app's directories; this
    will be used to find the correct app to import.
    """

    app = get_app(relpath)
    app.run_on_start_funcs()
    return TestApp(app)
