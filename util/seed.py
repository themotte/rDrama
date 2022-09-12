#!/usr/bin/env python3

import sys
from common import _operation

def run_seed(args):
    result = _operation("seed",[
        "cd service",
        "FLASK_APP=files/cli:app python3 -m flask seed_db",
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_seed(sys.argv)