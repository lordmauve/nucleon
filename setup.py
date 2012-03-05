from setuptools import setup, find_packages

from nucleon import __version__

import sys

INSTALL_REQUIRES = [
        'WebOb>=1.1.1',
        'gevent==1.0b1',  # will be installed with dependency_links
        'psycopg2>=2.2.1',
        'WebTest>=1.3.1',
        'puka>=0.0.3',
    ]
if sys.version_info < (2, 7):
    INSTALL_REQUIRES += [
        'argparse>=1.2.1',
        'ordereddict>=1.1',
    ]

setup(
    name="nucleon",
    version=__version__,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'nucleon = nucleon.commands:main',
        ]
    },
    package_data={
        'nucleon': ['skel/*'],
    },
    install_requires=INSTALL_REQUIRES,
    dependency_links=[
        'http://code.google.com/p/gevent/downloads/list',
    ]
)
