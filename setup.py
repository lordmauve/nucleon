from distutils.core import setup

from nucleon import __version__


setup(
    name="nucleon",
    version=__version__,
    packages=['nucleon'],
    scripts=['scripts/nucleon'],
    install_requires=[
        'WebOb>=1.1.1',
        'gevent==0.13.6',
        'psycopg2>=2.2.1',
        'WebTest>=1.3.1',
    ],
)
