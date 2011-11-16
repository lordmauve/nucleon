from setuptools import setup, find_packages

from nucleon import __version__


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
    install_requires=[
        'WebOb>=1.1.1',
        'gevent==0.13.6',
        'psycopg2>=2.2.1',
        'WebTest>=1.3.1',
    ],
)
