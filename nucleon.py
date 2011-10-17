#!/usr/bin/env python

"""Command-line interface for nucleon management out of the box.

setuptools creates a comparable command when the package is installed.

"""

import sys
import os.path
sys.path.insert(0, os.path.dirname(__file__))

from nucleon.commands import main

main()
