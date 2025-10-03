#!/usr/bin/env python3

import sys
from common import _operation

def run_test(args):
    # Skip the script name (first argument) and pass the rest to pytest
    pytest_args = args[1:] if len(args) > 1 else []

    result = _operation("tests", [
        [
            "python3",
            "-m", "pytest",
            "-s",
            "--cov=files",
            "--cov-report=html",
            "--cov-report=term",
        ] + pytest_args
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_test(sys.argv)