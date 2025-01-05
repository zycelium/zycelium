#!/usr/bin/env python
"""Test script for Zycelium."""

import sys
from pathlib import Path

from .utils import check_code, format_code, run_tests

PROJECT_ROOT = Path(__file__).parent.parent


def main() -> None:
    """Run the test script."""
    if not all(
        [
            format_code(PROJECT_ROOT),
            check_code(PROJECT_ROOT),
            run_tests(PROJECT_ROOT, coverage=True, capture_output=False),
        ]
    ):
        sys.exit(1)

    print("\n=== Tests Successful! ===\n")


if __name__ == "__main__":
    main()
