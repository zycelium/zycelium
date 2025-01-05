#!/usr/bin/env python
"""Build script for Zycelium."""

import sys
from pathlib import Path

from .utils import check_code, format_code, run_command, run_tests

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "zycelium"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"


def main() -> None:
    """Run the build script."""
    if not all(
        [
            format_code(PROJECT_ROOT),
            check_code(PROJECT_ROOT),
            run_tests(PROJECT_ROOT),
            run_command(
                ["sphinx-build", "-b", "html", "docs/source", "docs/build/html"],
                "Building documentation",
                cwd=str(PROJECT_ROOT),
            ),
            run_command(["poetry", "build"], "Building package", cwd=str(PROJECT_ROOT)),
        ]
    ):
        sys.exit(1)

    print("\n=== Build Successful! ===\n")


if __name__ == "__main__":
    main()
