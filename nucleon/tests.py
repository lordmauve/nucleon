import sys

from nucleon.loader import get_app

try:
    from webtest import TestApp
except ImportError:
    sys.exit('You must have WebTest installed for running tests')

try:
    import nose
    from nose.plugins import Plugin
except ImportError:
    sys.exit('You must have nose installed for running tests')


def get_test_app(relpath=None):
    """Build a test version of the app.

    If given, relpath is the path of a file within the app's directories; this
    will be used to find the correct app to import.
    """

    app = get_app(relpath)
    return TestApp(app)


def reset_database():
    """Delete data from all tables."""


def rollback_transaction():
    """Check the database connection state is clean.

    Rollback if not, then raise an error.
    """


def clean_database(test):
    test.setup = reset_database
    test.teardown = rollback_transaction


class TestDatabasePlugin(Plugin):
    """A plugin for nosetests that sets up a clean database."""

    def __init__(self, app):
        super(TestDatabasePlugin, self).__init__()
        self.app = app

    def begin(self):
        """Create the test database."""
        print "Create test database"

    def finalize(self):
        """Finalize the test database."""
        print "Drop test db"

    def beforeTest(self):
        """Reset data in the test database."""
        print "Reset test db"


def runtests(args):
    app = get_test_app()
    nose.main(addplugins=[TestDatabasePlugin(app)], argv=args)
