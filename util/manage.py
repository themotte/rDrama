#!/usr/bin/env python3

import sys
from common import error, run_help
from migrate import run_migrate
from test import run_test

if __name__=='__main__':

    if len(sys.argv) < 2:
        error("Usage: './manage.py <command> [options]'")

    name = sys.argv[1]
    args = sys.argv[1:]

    if name == "test":
        run_test(args)
    elif name == "migrate":
        run_migrate(args)
    elif name == "help":
        run_help()
    else:
        error("Not a command")