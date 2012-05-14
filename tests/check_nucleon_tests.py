from BeautifulSoup import BeautifulSoup
import string
import os
import sys

def main():
    #Get a list of all the elements in the current directory
    thisdir = os.path.abspath(os.path.dirname(__file__))
    dirlist = set(os.listdir(thisdir))

    # Look through all xunit test result files
    for d in dirlist:
        if d.startswith('test_xunit_'):
            f = open(d, 'r')
            parsed_file = BeautifulSoup(f.read())
            f.close()
            testsuite = parsed_file.testsuite
            if testsuite != None:
                if testsuite['failures'] != '0':
                    sys.stdout.write('False')
                    return

    sys.stdout.write('True')


if __name__ == "__main__":
    sys.exit(main())
