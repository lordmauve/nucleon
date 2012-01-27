# This script finds all the modules that have a testscript,
# runs the tests and outputs the results to an xml file (test_xunit_module.xml)
# Coverage statistics are obtained for all modules in coverage.xml
#
import os, sys

#Get a list of all the elements in the current directory
thisdir = os.path.abspath(os.path.dirname(__file__))
dirlist = os.listdir(thisdir)

# Add nucleon to sys.path
sys.path.append(os.path.abspath(os.path.dirname(thisdir)))

#Patch the standard library to use gevent
from  nucleon.main import bootstrap_gevent
bootstrap_gevent()

import shutil

from multiprocessing import Process

import nose

from coverage import coverage


#Get a list of all the elements in the current directory
thisdir = os.path.abspath(os.path.dirname(__file__))
dirlist = os.listdir(thisdir)

#Start collecting coverage data
cov = coverage()
cov.start()

#For each item in the list, first check whether it's a dir, then check whether a testscript and app exists in that dir.
#If both a testscript and an app exist, then run the test.
for d in dirlist:
    if os.path.isdir(d) == True:
        if os.path.exists(os.path.join(d, 'tests.py')) and os.path.exists(os.path.join(d, 'app.py')):

            #Change into the directory of the module we are testing
            os.chdir(os.path.abspath(d))

            #Run the nosetest with xunit enabled
            args = ['nosetests','--with-xunit','--xunit-file','../test_xunit_'+d+'.xml']
            nose.run(argv=args)

            #Move back in the original dir
            os.chdir(os.path.abspath(thisdir))


#Stop collecting the coverage data and convert it into XML format
cov.stop()
cov.save()
cov.xml_report()
