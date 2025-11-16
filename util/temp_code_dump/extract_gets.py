#!/usr/bin/env python3
"""
Extract the last 100 GET requests from access.log for benchmarking.
"""

import re
from collections import deque

def extract_last_gets(log_file='access.log', count=1000):
    """
    Extract the last N GET requests from an access log file.

    Returns a list of tuples: (method, path, query_string)
    """
    # Pattern to match log entries and extract HTTP method and path
    # Format: IP - - [timestamp] "METHOD /path HTTP/version" status size ...
    pattern = re.compile(r'"(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS) ([^\s]+) HTTP/[^"]*"')

    # Use deque with maxlen to efficiently keep only the last N GET requests
    last_gets = deque(maxlen=count)

    with open(log_file, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                method, full_path = match.groups()
                if method == 'GET':
                    # Split path and query string if present
                    if '?' in full_path:
                        path, query = full_path.split('?', 1)
                    else:
                        path, query = full_path, ''

                    last_gets.append((method, path, query))

    return list(last_gets)


def main():
    gets = extract_last_gets()

    print(f"Extracted {len(gets)} GET requests:\n")

    for i, (method, path, query) in enumerate(gets, 1):
        if query:
            print(f"{i}. {method} {path}?{query}")
        else:
            print(f"{i}. {method} {path}")

    # Also save to a file for easy reuse
    output_file = 'last_100_gets.txt'
    with open(output_file, 'w') as f:
        for method, path, query in gets:
            if query:
                f.write(f"{method} {path}?{query}\n")
            else:
                f.write(f"{method} {path}\n")

    print(f"\n✓ Saved to {output_file}")


if __name__ == '__main__':
    main()
