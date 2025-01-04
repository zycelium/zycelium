"""Setup development environment."""

import sys
from typing import NoReturn

from .utils import run_command


def get_testpypi_token() -> str:
    """Get TestPyPI token from user input."""
    print("\nTo publish to TestPyPI, you need an API token.")
    print("1. Go to https://test.pypi.org/manage/account/token/")
    print("2. Create a new token with scope 'Entire account'")
    print("3. Copy the token value")
    return input("\nEnter your TestPyPI token (will be hidden in config): ").strip()


def configure_poetry() -> bool:
    """Configure poetry with required settings."""
    commands = [
        {
            "cmd": [
                "poetry",
                "config",
                "repositories.testpypi",
                "https://test.pypi.org/legacy/",
            ],
            "description": "Configuring TestPyPI repository",
        },
    ]

    # Configure TestPyPI token
    token = get_testpypi_token()
    if token:
        commands.append(
            {
                "cmd": [
                    "poetry",
                    "config",
                    "pypi-token.testpypi",
                    token,
                ],
                "description": "Configuring TestPyPI authentication token",
            }
        )

    commands.extend(
        [
            {
                "cmd": ["poetry", "install"],
                "description": "Installing project dependencies",
            },
            {
                "cmd": ["poetry", "lock", "--check"],
                "description": "Verifying poetry.lock is up to date",
            },
        ]
    )

    for command in commands:
        if not run_command(command["cmd"], command["description"]):
            return False
    return True


def main() -> NoReturn:
    """Run the development setup script."""
    print("Setting up development environment...\n")

    if configure_poetry():
        print("\n=== Development setup completed successfully! ===\n")
        sys.exit(0)
    else:
        print("\n=== Development setup failed! ===\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
