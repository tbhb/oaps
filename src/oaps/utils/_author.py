"""Author information resolution utilities."""

import os
import subprocess
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AuthorInfo:
    """Resolved author information.

    Attributes:
        name: Author name, or None if not found.
        email: Author email, or None if not found.
    """

    name: str | None
    email: str | None


def get_author_info() -> AuthorInfo:
    """Resolve author info from environment variables or git config.

    Resolution order:
    1. Environment variables (OAPS_AUTHOR_NAME, OAPS_AUTHOR_EMAIL)
    2. Git config (user.name, user.email)

    Returns:
        AuthorInfo with resolved name and email (either may be None).
    """
    name = os.environ.get("OAPS_AUTHOR_NAME") or _git_config("user.name")
    email = os.environ.get("OAPS_AUTHOR_EMAIL") or _git_config("user.email")

    return AuthorInfo(name=name, email=email)


def _git_config(key: str) -> str | None:
    """Read a value from git config.

    Args:
        key: Git config key (e.g., "user.name").

    Returns:
        The config value, or None if not set or git fails.
    """
    # Validate key to prevent injection
    if not key.replace(".", "").replace("_", "").isalnum():
        return None

    try:
        result = subprocess.run(  # noqa: S603
            ["git", "config", "--get", key],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None
