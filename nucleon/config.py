"""A system for loading application configuration from ini-style files.

To allow an application's configuration to be reconfigured in different
environments, only configuration properties associated with a particular
"current" environment are used.

"""

import os
import logging
from ConfigParser import (
    SafeConfigParser as ConfigParser,
    NoSectionError
)

DEFAULT_ENVIRONMENT = 'default'
SETTINGS_FILENAME = 'app.cfg'


class ConfigurationError(AttributeError):
    """The application instance was misconfigured."""


class Settings(object):
    """A class to encapsulate settings in different environments.

    Key to this class is the ability to read configuration from one specific
    environment.

    To allow this to be determined after the app is loaded, the environment can
    be changed. However, this would allow users to inadvertently take settings
    from different environments if they cached settings or made connections
    before the final environment was chosen. To avoid this, reading a property
    locks the active environment.

    """
    def __init__(self):
        self._settings = {}
        self._locked = False
        self._haveconfig = False

    @staticmethod
    def for_app_file(filename, environment=DEFAULT_ENVIRONMENT):
        """Load the settings that correspond to the given Python app file."""
        base = os.path.dirname(filename)
        path = os.path.join(base, SETTINGS_FILENAME)
        s = Settings()
        s._load(path)
        return s

    def _load(self, filename, environment=DEFAULT_ENVIRONMENT):
        """Load settings from the named environment in filename."""
        if self._locked:
            raise ConfigurationError("Settings are locked")
        self._config = ConfigParser()
        self._haveconfig = False
        try:
            with open(filename, 'rU') as conf:
                self._config.readfp(conf)
            self._haveconfig = True
        except IOError:
            logging.warning("Couldn't open configuration file " + filename)
        self._set_environment(environment)

    def _set_environment(self, environment):
        """Switch to a different environment.

        Raises ConfigurationError if the environment has already been locked.
        """
        if self._locked:
            raise ConfigurationError("Settings environment is locked")

        # Don't error if no config is loaded; This sitation is valid as long as
        # the app never tries to access settings, and if it does an error will
        # be raised at that point.
        if not self._haveconfig:
            return

        name = os.environ.get('NUCLEON_CONFIGURATION', environment)
        try:
            settings = self._config.items(name)
        except NoSectionError:
            raise ConfigurationError("No such environment: " + name)
        self._settings = dict(settings)  # FIXME: intern the keys
        self._settings['environment'] = name

    def __setattr__(self, key, value):
        if not key.startswith('_'):
            raise TypeError("Settings are immutable")
        super(Settings, self).__setattr__(key, value)

    def __getattr__(self, key):
        self._locked = True
        try:
            return self._settings[key]
        except KeyError:
            raise ConfigurationError(key)


settings = Settings()
