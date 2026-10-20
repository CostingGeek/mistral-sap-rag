#!/usr/bin/env python3
"""
Regression Test Runner for SAP RAG Application

This script runs the complete regression test suite with proper configuration.
Usage:
    python run_regression_tests.py              # Run all tests
    python run_regression_tests.py --group api   # Run API tests only
    python run_regression_tests.py --group integrations  # Run integration tests
    python run_regression_tests.py --group services   # Run service tests
    python run_regression_tests.py --verbose       # Verbose output
    python run_regression_tests.py --coverage      # With coverage report
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Test groups and their paths
TEST_GROUPS = {
    "all": "backend/tests/",
    "api": "backend/tests/api/",
    "integrations": "backend/tests/integrations/",
    "services": "backend/tests/services/",
}


def run_tests(test_path: str, verbose: bool = False, coverage: bool = False) -> int:
    """Run pytest on the specified test path."""
    cmd = [
        sys.executable, "-m", "pytest",
        test_path,
        "--tb=short",
    ]
    
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")
    
    if coverage:
        cmd.extend(["--cov=backend", "--cov-report=term"])
    
    # Run the command
    result = subprocess.run(cmd, capture_output=not verbose, text=True)
    
    if verbose:
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    else:
        # Only show summary for non-verbose
        if result.stdout:
            lines = result.stdout.split('\n')
            # Show last 10 lines (summary)
            for line in lines[-10:]:
                if line.strip():
                    print(line)
        if result.stderr:
            lines = result.stderr.split('\n')
            for line in lines[-5:]:
                if line.strip():
                    print(line, file=sys.stderr)
    
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run regression tests for SAP RAG application"
    )
    parser.add_argument(
        "--group", "-g",
        choices=list(TEST_GROUPS.keys()),
        default="all",
        help="Test group to run (default: all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage"
    )
    
    args = parser.parse_args()
    
    test_path = TEST_GROUPS[args.group]
    
    print(f"Running {args.group} tests...")
    print(f"Test path: {test_path}")
    print()
    
    return_code = run_tests(test_path, args.verbose, args.coverage)
    
    if return_code == 0:
        print("\n[PASS] All tests passed!")
    else:
        print(f"\n[FAIL] Some tests failed (exit code: {return_code})")
    
    sys.exit(return_code)


if __name__ == "__main__":
    main()
