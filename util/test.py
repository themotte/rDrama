#!/usr/bin/env python3

import sys
from common import _operation

def run_test(args):
    result = _operation("tests", [
        [
            "python3",
            "-m", "pytest",
            "-s",
            "--cov=files",
            "--cov-report=term-missing",
            "--cov-report=html",
        ]
    ])

    sys.exit(result.returncode)

if __name__=='__main__':
    run_test(sys.argv)