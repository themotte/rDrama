#!/usr/bin/env python3

import sys
from common import _operation

def run_command(argv):
    result = _operation(f"command",[
        [
            "python3",
            "-m", "flask",
        ] + argv[1:]
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_command(sys.argv)
