#!/usr/bin/env python3
"""
Benchmark script that replays GET requests and measures response times.
"""

import time
import requests
from typing import List, Tuple
import sys

def load_requests(filename='last_100_gets.txt') -> List[Tuple[str, str]]:
    """
    Load GET requests from file.
    Returns list of (method, url_path) tuples.
    """
    requests_list = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split(' ', 1)
                if len(parts) == 2:
                    method, path = parts
                    requests_list.append((method, path))
    return requests_list


def benchmark_request(base_url: str, method: str, path: str) -> Tuple[str, float, int, str]:
    """
    Execute a single request and measure response time.
    Returns (url, duration_ms, status_code, error_msg).
    """
    url = f"{base_url}{path}"

    try:
        start_time = time.time()
        response = requests.get(url, timeout=30, allow_redirects=False)
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds

        return (url, duration, response.status_code, "")
    except requests.exceptions.Timeout:
        return (url, 30000.0, 0, "TIMEOUT")
    except requests.exceptions.ConnectionError as e:
        return (url, 0.0, 0, f"CONNECTION_ERROR: {str(e)[:50]}")
    except Exception as e:
        return (url, 0.0, 0, f"ERROR: {str(e)[:50]}")


def main():
    base_url = "http://localhost"

    # Allow custom base URL from command line
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"Loading requests from last_100_gets.txt...")
    requests_list = load_requests()
    print(f"Loaded {len(requests_list)} requests\n")

    print(f"Benchmarking against {base_url}...")
    print("=" * 80)

    results = []

    for i, (method, path) in enumerate(requests_list, 1):
        url, duration, status, error = benchmark_request(base_url, method, path)
        results.append((url, duration, status, error))

        # Show progress
        if error:
            print(f"[{i}/{len(requests_list)}] {status} - {error}")
        else:
            print(f"[{i}/{len(requests_list)}] {status} - {duration:>8.2f}ms - {path[:60]}")

    print("\n" + "=" * 80)
    print("\nRESULTS (sorted by duration, most expensive first):\n")

    # Sort by duration (descending)
    results.sort(key=lambda x: x[1], reverse=True)

    # Calculate statistics
    successful_results = [(url, dur, status, err) for url, dur, status, err in results if not err and status < 400]
    failed_results = [(url, dur, status, err) for url, dur, status, err in results if err or status >= 400]

    if successful_results:
        durations = [dur for _, dur, _, _ in successful_results]
        total_time = sum(durations)
        avg_time = total_time / len(durations)
        min_time = min(durations)
        max_time = max(durations)

        print(f"Statistics for {len(successful_results)} successful requests:")
        print(f"  Total time: {total_time:>10.2f}ms")
        print(f"  Average:    {avg_time:>10.2f}ms")
        print(f"  Min:        {min_time:>10.2f}ms")
        print(f"  Max:        {max_time:>10.2f}ms")
        print()

    if failed_results:
        print(f"Failed/Error requests: {len(failed_results)}")
        print()

    # Display top 20 slowest requests
    print("Top 20 slowest requests:")
    print("-" * 80)

    for i, (url, duration, status, error) in enumerate(results[:20], 1):
        if error:
            print(f"{i:2d}. {duration:>8.2f}ms [{status}] {error}")
            print(f"    {url}")
        else:
            print(f"{i:2d}. {duration:>8.2f}ms [{status}] {url}")

    # Save detailed results to file
    output_file = 'benchmark_results.txt'
    with open(output_file, 'w') as f:
        f.write("Benchmark Results (sorted by duration)\n")
        f.write("=" * 80 + "\n\n")

        for i, (url, duration, status, error) in enumerate(results, 1):
            if error:
                f.write(f"{i:3d}. {duration:>10.2f}ms [{status:3d}] {error}\n")
                f.write(f"     {url}\n")
            else:
                f.write(f"{i:3d}. {duration:>10.2f}ms [{status:3d}] {url}\n")

    print(f"\n✓ Full results saved to {output_file}")


if __name__ == '__main__':
    main()
