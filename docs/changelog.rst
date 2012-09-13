Changelog
=========

Changes to Nucleon:

Version 0.0.2
-----------
* Now uses gevent v1.0b4
* Removed dependency on Beautiful Soup
* Added support for type and sequences in SQL scripts
* Added transaction support for database API
* Reverted the signature of make_reinitialize_script to avoid backwards-incompatible changes
* Returned the row count for UPDATE and DELETE queries
* Fix: Make nucleon.validation importable
* Allow no-op change of settings environment

Version 0.0.1-gevent
-----------
Initial Version
