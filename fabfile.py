import sys
import re
from os.path import dirname, join

from fabric.api import env, run, sudo, put, local, cd, get
from fabric.decorators import hosts, runs_once
from fabric.contrib.project import rsync_project
from fabric.contrib.files import exists

env.user = 'nucleon'
env.key_filename = '/var/lib/jenkins/.ssh/nucleon_id_rsa'


@hosts('bruges.vertulabs.co.uk')
def deploy_nucleondocs():
    """Generate nucleon docs and deploy to the docs webserver"""

    PATH = '/srv/docs_webserver/docs/nucleon/'

    build_nucleondocs()

    # Copy generated docs to docs_webserver on target machine
    sudo('chown -R %s: %s' % (env.user, PATH))
    rsync_project(remote_dir=PATH, local_dir=join(dirname(__file__), 'docs/_build/html/'), delete=True)
    sudo('chown -R docs:www-data ' + PATH)


@runs_once
def build_nucleondocs():
    """Generate nucleon docs (uses Sphinx)"""
    path = join(dirname(__file__),'docs')
    local('cd %s && make html' % path)


#@hosts('geneva.vertulabs.co.uk')
def run_nucleon_tests():

    JOB_DIR = '/home/nucleon/nucleon-core'
    VIRTUALENV_PATH = '%s/NUCLEON_ENV' % JOB_DIR
    NUCLEON_RESULTS = '%s/workspace/tests/test_xunit_*' % JOB_DIR
    RSYNC_EXCLUSIONS =['*.rst','*.pyc','*.i']
    JENKINS_RESULTS_DIR = '/var/lib/jenkins/jobs/nucleon-tests/workspace/tests/'
    NUCLEON_COVER_XML = '%s/workspace/tests/coverage.xml' % JOB_DIR


    #Delete the virtualenv, if it exists
    if exists(JOB_DIR):
        run('rm -rf %s' % JOB_DIR)

    #Create new virtual env
    run('mkdir %s' % JOB_DIR)
    run('mkdir %s' %VIRTUALENV_PATH)
    run('virtualenv %s' % VIRTUALENV_PATH)


    #Copy the nucleon project from the Jenkins server to the Nucleon server
    rsync_project(remote_dir=JOB_DIR, local_dir=dirname(__file__), delete=True, exclude=RSYNC_EXCLUSIONS)


    #Install nose
    run('%s/bin/pip install nose>=1.1.2' % VIRTUALENV_PATH)

    #Install the covergae module
    run('%s/bin/pip install coverage>=3.5.1' % VIRTUALENV_PATH)


    # Install nucleon in the virtual env
    with cd('%s/workspace' % JOB_DIR):
        run('%s/bin/python setup.py install' % VIRTUALENV_PATH)

    # Run the tests in the virtual env
    with cd('%s/workspace/tests' % JOB_DIR):
       run('%s/bin/python nucleon_tests.py' % VIRTUALENV_PATH)


    #copy the resulst back up to the Jenkins server
    get(NUCLEON_RESULTS, local_path='%s' % JENKINS_RESULTS_DIR)
    get(NUCLEON_COVER_XML, local_path='%s' % JENKINS_RESULTS_DIR)
