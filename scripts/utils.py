"""Shared utilities for scripts."""

import subprocess
import sys
from pathlib import Path
from typing import Optional


def run_command(
    cmd: list[str],
    description: str,
    *,
    cwd: Optional[str] = None,
    capture_output: bool = True,
) -> bool:
    """Run a command and return True if successful.

    Args:
        cmd: Command and arguments to run
        description: Description of the command for output
        cwd: Working directory for the command
        capture_output: Whether to capture command output
    """
    print(f"\n=== {description} ===\n")

    kwargs = {"cwd": cwd}
    if capture_output:
        kwargs["capture_output"] = True
        kwargs["text"] = True

    result = subprocess.run(cmd, **kwargs)

    if result.returncode == 0:
        print("Success!")
        return True

    if capture_output:
        print(f"Failed: {result.stderr}", file=sys.stderr)
    return False


def format_code(project_root: Path) -> bool:
    """Format code using isort and black."""
    return all(
        [
            run_command(
                ["isort", "."],
                "Running isort",
                cwd=str(project_root),
                capture_output=False,
            ),
            run_command(
                ["black", "."],
                "Running black",
                cwd=str(project_root),
                capture_output=False,
            ),
        ]
    )


def check_code(project_root: Path) -> bool:
    """Run code quality checks using flake8 and mypy."""
    return all(
        [
            run_command(
                ["flake8", "src", "tests"], "Running flake8", cwd=str(project_root)
            ),
            run_command(
                ["mypy", "src", "tests"], "Running mypy", cwd=str(project_root)
            ),
        ]
    )


def run_tests(
    project_root: Path, coverage: bool = False, capture_output: bool = True
) -> bool:
    """Run pytest with optional coverage reporting.

    Args:
        project_root: Project root directory
        coverage: Whether to generate coverage reports
        capture_output: Whether to capture command output
    """
    cmd = ["pytest"]
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html"])
    return run_command(
        cmd, "Running tests", cwd=str(project_root), capture_output=capture_output
    )
