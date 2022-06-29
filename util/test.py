#!/usr/bin/env python3

import sys
from common import _operation

def run_test(args):
    result = _operation("tests",[
        "cd service",
        "FLASK_APP=files/cli:app python3 -m flask db upgrade",
        "python3 -m pytest -s",
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_test(sys.argv)