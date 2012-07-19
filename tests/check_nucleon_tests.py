import os
from xml.etree.ElementTree import parse


def results_files():
    """Iterate over all xunit test result files"""
    thisdir = os.path.abspath(os.path.dirname(__file__))
    dirlist = set(os.listdir(thisdir))

    for d in dirlist:
        if d.startswith('test_xunit_'):
            yield d


def tests_passed(filename):
    """Determine if the tests in an xunit test result file were successful."""
    rs = parse(filename).getroot()
    return rs.get('failures') == '0' and rs.get('errors') == '0'


def main():
    print all(tests_passed(d) for d in results_files())


if __name__ == "__main__":
    main()
