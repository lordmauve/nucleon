import sys
import re
from os.path import dirname, join

from fabric.api import env, run, sudo, put, local
from fabric.context_managers import cd
from fabric.decorators import hosts, runs_once
from fabric.contrib.project import rsync_project


@hosts('bruges.vertulabs.co.uk')
def deploy_nucleondocs():

    """Generate nucleon docs and deploy to the docs webserver"""

    PATH = '/srv/docs_webserver/docs/nucleon/'

    build_nucleondocs()

    # Copy generated docs to docs_webserver on target machine
    sudo('chown -R %s: %s' % (env.user, PATH))
    rsync_project(remote_dir=PATH, local_dir=join(dirname(__file__),'docs/_build/html'))
    sudo('chown -R docs:www-data ' + PATH)


@runs_once
def build_nucleondocs():

    # Generate nucleon docs (uses Sphinx)
    with cd(join(dirname(__file__),'docs')):
        local('make html')

