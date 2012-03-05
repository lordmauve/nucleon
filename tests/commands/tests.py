import os
import os.path
import shutil
import stat
import tempfile


def is_executable(path):
    """Return True if file is executable"""
    exe_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    return os.stat(path).st_mode & exe_bits


def test_new_app():
    """Test that we can create a new app.

    Also tests that the app has appropriate permissions.
    """

    from nucleon.commands import new

    destdir = tempfile.mktemp()
    try:
        new(destdir)
        assert os.path.isfile(os.path.join(destdir, 'app.py'))
        assert os.path.isfile(os.path.join(destdir, 'app.cfg'))
        assert os.path.isfile(os.path.join(destdir, 'database.sql'))

        tests_py = os.path.join(destdir, 'tests.py')
        assert os.path.isfile(tests_py)
        assert not is_executable(tests_py)
    finally:
        shutil.rmtree(destdir, ignore_errors=True)

