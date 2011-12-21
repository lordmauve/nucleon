#!/usr/bin/env python
"""
It monkeypatches python and runs specific function.
Thanks to it we can run nosetests with proper gevent handling.

Example usage:
../../gex.py nose:nosetests -v -s

Expects https://github.com/SurveyMonkey/GeventUtil to be installed. It is not a part of pip.
We may consider making it a part of nucleon.
"""


from geventutil.script import main
main()

