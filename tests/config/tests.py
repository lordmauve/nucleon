from nose.tools import eq_, raises
from nucleon import tests
from nucleon.config import settings, Settings, ConfigurationError

tests.get_test_app(__file__)


def test_config_loaded():
    """Test that settings are loaded and the default environment is test."""
    eq_(settings.environment, 'test')
    eq_(settings.database, 'test_database')
    eq_(settings.amqp, 'test_amqp')


@raises(TypeError)
def test_settings_environment_immutable():
    """Test that we cannot override the environment"""
    settings.environment = 'test'


@raises(TypeError)
def test_settings_value_immutable():
    """Test that we cannot override a setting"""
    settings.database = 'test'


@raises(ConfigurationError)
def test_invalid_environment():
    """Test that we cannot select an environment that doesn't exist"""
    settings2 = Settings.for_app_file(__file__)
    settings2._set_environment('nokia-it')


@raises(ConfigurationError)
def test_change_environment():
    """Test that the environment is immutable once a property has been read"""
    settings2 = Settings.for_app_file(__file__)
    eq_(settings2.database, 'default_database')
    settings2._set_environment('test')


def test_environment_switch():
    """Test that we can switch environment"""
    settings2 = Settings.for_app_file(__file__)
    eq_(settings2._settings['database'], 'default_database')
    settings2._set_environment('test')
    eq_(settings2.database, 'test_database')


def test_environment_env():
    "Test that the default environment can be selected by an env variable"
    import os
    eq_(settings.database, 'test_database')
    os.environ['NUCLEON_CONFIGURATION'] = 'production'

    try:
        settings2 = Settings.for_app_file(__file__)
        eq_(settings2.database, 'production_database')
    finally:
        del(os.environ['NUCLEON_CONFIGURATION'])
