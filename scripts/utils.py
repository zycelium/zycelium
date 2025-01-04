"""Shared utilities for scripts."""

import subprocess
import sys
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
