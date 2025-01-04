#!/usr/bin/env python
"""Build script for Zycelium."""

import sys
from pathlib import Path

from .utils import run_command

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src" / "zycelium"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"


def main() -> None:
    """Run the build script."""
    # Format code
    if not all(
        [
            run_command(
                ["isort", "."],
                "Running isort",
                cwd=str(PROJECT_ROOT),
                capture_output=False,
            ),
            run_command(
                ["black", "."],
                "Running black",
                cwd=str(PROJECT_ROOT),
                capture_output=False,
            ),
            run_command(
                ["flake8", "src", "tests"], "Running flake8", cwd=str(PROJECT_ROOT)
            ),
            run_command(
                ["mypy", "src", "tests"], "Running mypy", cwd=str(PROJECT_ROOT)
            ),
            run_command(
                ["pytest"], "Running pytest with coverage", cwd=str(PROJECT_ROOT)
            ),
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
