import posixpath
from contextlib import contextmanager
from os.path import dirname, join, abspath

from fabric.api import env, run, sudo, local, cd, get, task, put
from fabric.decorators import hosts, runs_once
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists
from fabric.context_managers import prefix, settings


@task
@hosts('bruges.vertulabs.co.uk')
def deploy_nucleondocs():
    """Generate nucleon docs and deploy to the docs webserver"""

    PATH = '/srv/docs_webserver/docs/nucleon/'

    build_nucleondocs()

    # Copy generated docs to docs_webserver on target machine
    sudo('chown -R %s: %s' % (env.user, PATH))
    rsync_project(
        remote_dir=PATH,
        local_dir=join(dirname(__file__), 'docs/_build/html/'),
        delete=True)
    sudo('chown -R docs:www-data ' + PATH)


@task
@runs_once
def build_nucleondocs():
    """Generate nucleon docs (uses Sphinx)"""
    path = join(dirname(__file__), 'docs')
    local('cd %s && make html' % path)


@contextmanager
def virtualenv(path):
    """Context manager that performs commands with an active virtualenv, eg:

    path is the path to the virtualenv to apply

    >>> with virtualenv(env):
            run('python foo')

    """
    activate = posixpath.join(path, 'bin/activate')
    if not exists(activate):
        raise OSError("Cannot activate virtualenv %s" % path)
    with prefix('. %s' % activate):
        yield


RSYNC_EXCLUSIONS = ['.hg', '*.swp', '*.pyc', '*.i']


@task
def run_nucleon_tests():
    """Run nucleon tests on a staging server."""
    # Build source distribution
    version = local('python setup.py -V', capture=True)
    local('rm -rf dist/*')
    local('python setup.py sdist')

    # Delete the virtualenv, if it exists
    run('rm -rf nucleon')
    run('mkdir -p nucleon')

    # Copy and unpack source distribution
    put('dist/nucleon-%s.tar.gz' % version, 'nucleon/')
    run('tar xzf nucleon/nucleon-%s.tar.gz -C nucleon/' % version)

    # Copy tests to remote machine
    rsync_project(
        remote_dir='nucleon/tests',
        local_dir=abspath(dirname(__file__)) + '/tests/',
        delete=True,
        exclude=RSYNC_EXCLUSIONS)

    with cd('nucleon'):
        # Create new virtual env
        run('virtualenv NUCLEON_ENV')

        with virtualenv('~/nucleon/NUCLEON_ENV'):
            # Install distribution and dependencies into virtualenv
            run('pip install "nose>=1.1.2" "coverage>=3.5.1" pylint mock')
            with cd('nucleon-%s' % version):
                run('python setup.py develop')

            with settings(warn_only=True):
                # Run the tests
                with cd('tests'):
                    run('python nucleon_tests.py')

                # Generate pylint report
                with cd('nucleon-%s' % version):
                    out = run('pylint --output-format=parseable nucleon')

    # Retrieve the results
    get('nucleon/tests/test_xunit_*', local_path='tests/')
    get('nucleon/tests/coverage.xml', local_path='tests/')
    with open('tests/pylint.report', 'w') as f:
        f.write(out)
