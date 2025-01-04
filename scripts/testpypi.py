"""Build and publish package to TestPyPI."""

import sys
from pathlib import Path

from .utils import run_command


def main() -> int:
    """Build and publish to TestPyPI."""
    # Clean up any old builds
    for path in Path("dist").glob("*"):
        path.unlink()

    if not all(
        [
            run_command(["poetry", "build"], "Building package"),
            run_command(
                ["poetry", "publish", "--repository", "testpypi"],
                "Publishing to TestPyPI",
            ),
        ]
    ):
        return 1

    print("Successfully published to TestPyPI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
