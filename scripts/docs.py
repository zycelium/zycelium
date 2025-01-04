"""Build and publish documentation."""

import sys
from pathlib import Path

from .utils import run_command

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_SOURCE = DOCS_DIR / "source"
DOCS_BUILD = DOCS_DIR / "build"
DOCS_HTML = DOCS_BUILD / "html"


def main() -> int:
    """Build and publish documentation."""
    # Ensure build directory exists
    DOCS_BUILD.mkdir(parents=True, exist_ok=True)

    # Clean existing build
    if DOCS_HTML.exists():
        for path in DOCS_HTML.glob("**/*"):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        DOCS_HTML.rmdir()

    # Build documentation
    if not run_command(
        ["sphinx-build", "-b", "html", str(DOCS_SOURCE), str(DOCS_HTML)],
        "Building documentation",
        cwd=str(PROJECT_ROOT),
    ):
        return 1

    print("\nDocumentation built successfully!")
    print(f"You can view it at: {DOCS_HTML}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
