#!/usr/bin/env python3

import sys
from common import _operation

def run_migrate(args):
    command = 'upgrade'

    if len(args) > 1:
        command = args[1]

    result = _operation(command,[
        "export FLASK_APP=files/cli:app",
        f"python3 -m flask db {command}",
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_migrate(sys.argv)