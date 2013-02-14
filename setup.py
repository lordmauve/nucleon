from setuptools import setup, find_packages

import sys

INSTALL_REQUIRES = [
        'WebOb>=1.1.1',
        'gevent==1.0b4',  # will be installed with dependency_links
        'psycopg2>=2.2.1',
        'WebTest>=1.3.1'
    ]
if sys.version_info < (2, 7):
    INSTALL_REQUIRES += [
        'argparse>=1.2.1',
        'ordereddict>=1.1',
    ]

setup(
    name="nucleon",
    version='0.1',
    description="A gevent-based microframework for building RESTful web services that provide AMQP interfaces.",
    long_description=open('README.rst').read(),
    url='https://docs.vertulabs.co.uk/nucleon/',
    author='Vertu Infrastructure Development Team',
    author_email='ops@vertulabs.co.uk',
    packages=find_packages(),
    namespace_packages=['nucleon'],
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
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
