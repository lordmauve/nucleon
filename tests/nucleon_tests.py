# This script finds all the modules that have a testscript,
# runs the tests and outputs the results to an xml file (test_xunit_module.xml)
# Coverage statistics are obtained for all modules in coverage.xml
#

# Patch the standard library to use gevent
import nucleon
from nucleon.main import bootstrap_gevent
bootstrap_gevent()

import os
import sys

thisdir = os.path.abspath(os.path.dirname(__file__))

# Add nucleon to sys.path
# sys.path.append(os.path.abspath(os.path.dirname(thisdir)))

# Imports for this script
import nose
from coverage import coverage
from gevent.hub import get_hub
import psycopg2.extensions
import sys


def unload_nucleon():
    """Unload all nucleon code from sys.modules."""
    psycopg2.extensions.set_wait_callback(None)
    get_hub().destroy(destroy_loop=True)
    for k in sys.modules.keys():
        if k.split('.')[0] == 'nucleon':
            del(sys.modules[k])


#Get a list of all the elements in the current directory
dirlist = set(os.listdir(thisdir))
if sys.argv[1:]:
    dirlist = list(dirlist.intersection(sys.argv[1:]))

#Start collecting coverage data
cov = coverage(branch=True, source=nucleon.__path__)
cov.start()

#For each item in the list, first check whether it's a dir, then check whether
#a testscript and app exists in that dir.
#If both a testscript and an app exist, then run the test.
for d in dirlist:
    if os.path.isdir(d) == True:
        if os.path.exists(os.path.join(d, 'tests.py')):

            #Change into the directory of the module we are testing
            os.chdir(os.path.abspath(d))

            # Unload loaded modules
            unload_nucleon()

            #Run the nosetest with xunit enabled
            args = ['nosetests', '-v', '-s', '--nologcapture',
            '--with-xunit', '--xunit-file', '../test_xunit_' + d + '.xml',
            ]
            nose.run(argv=args)

            #Move back in the original dir
            os.chdir(os.path.abspath(thisdir))

#Stop collecting the coverage data and convert it into XML format
cov.stop()
cov.save()
cov.xml_report(outfile='coverage.xml.in')

# Rewrite coverage report to remove absolute paths
nucleon_path = os.path.dirname(nucleon.__path__[0]) + '/'
nucleon_mod = nucleon_path.replace('/', '.')
with open('coverage.xml.in', 'r') as input:
    with open('coverage.xml', 'w') as output:
        for l in input:
            l = l.replace(nucleon_path, '')
            l = l.replace(nucleon_mod, '')
            output.write(l)

cov.report(file=sys.stdout)
