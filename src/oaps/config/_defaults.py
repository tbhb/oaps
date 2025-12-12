"""Default configuration values.

This module defines the built-in default configuration values that are used
when no other configuration sources provide values.

Note: DEFAULT_CONFIG is intentionally a plain dict for type compatibility
with functions like deep_merge. The merge functions create copies, so mutation
of the original is not a concern in practice.
"""

from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
    "logging": {
        "level": "info",
        "format": "json",
        "file": "",
    },
    "project": {
        "name": "",
        "version": "",
    },
    "ideas": {
        "tags": {
            "productivity": "Ideas related to improving efficiency and workflows",
            "ai": "Ideas involving artificial intelligence or machine learning",
            "automation": "Ideas for automating manual processes",
            "tooling": "Developer tools and infrastructure",
            "ux": "User experience improvements",
            "architecture": "System design and architecture",
            "process": "Team processes and methodologies",
            "research": "Research directions and experiments",
        },
        "extend_tags": {},
    },
}
