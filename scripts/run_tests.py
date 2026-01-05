#!/usr/bin/env python3
"""
Test runner script for Sherlock Discord Bot.
Wraps pytest to provide a unified interface for running different test suites
and checking coverage requirements.
"""

import argparse
import subprocess
import sys


def run_command(command, cwd=None, capture_output=False):
    """Run a shell command and return a CompletedProcess result."""
    print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, cwd=cwd, check=True, text=True, capture_output=capture_output
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if capture_output:
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
        # Return a CompletedProcess-like object for consistent API
        return subprocess.CompletedProcess(
            args=e.cmd,
            returncode=e.returncode,
            stdout=e.stdout if capture_output else "",
            stderr=e.stderr if capture_output else "",
        )


def run_tests(suite=None, coverage=True):
    """Run tests using pytest."""
    base_cmd = ["pytest"]

    if suite:
        if suite == "unit":
            base_cmd.append("tests/unit")
        elif suite == "integration":
            base_cmd.append("tests/integration")
        elif suite == "e2e":
            # Assuming e2e tests might be in a different folder or marked
            base_cmd.append("tests/e2e")
        else:
            print(f"Unknown test suite: {suite}")
            return False

    if not coverage:
        # Override addopts or explicitly disable if needed,
        # but pytest.ini has it enabled by default.
        # We can use --no-cov to disable it if we want.
        base_cmd.append("--no-cov")

    result = run_command(base_cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Run tests for Sherlock Bot")
    parser.add_argument(
        "--suite",
        choices=["unit", "integration", "e2e", "all"],
        default="all",
        help="Test suite to run",
    )
    parser.add_argument("--no-cov", action="store_true", help="Disable coverage reporting")

    args = parser.parse_args()

    suite = args.suite if args.suite != "all" else None
    success = run_tests(suite, coverage=not args.no_cov)

    if success:
        print("\n✅ Tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
