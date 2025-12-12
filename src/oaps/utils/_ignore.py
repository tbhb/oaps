"""Gitignore-style pattern matching using pathspec.

This module provides utilities for loading and matching gitignore patterns
from various sources (worktree gitignore, OAPS gitignore, and defaults).
"""

from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 - Used at runtime in function parameters
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pathspec import PathSpec


DEFAULT_IGNORE_PATTERNS: frozenset[str] = frozenset(
    {
        "*.pyc",
        "__pycache__/",
        ".git/",
        ".oaps/",
        "node_modules/",
        ".venv/",
        "*.egg-info/",
    }
)
"""Default patterns to ignore when watching files.

These patterns are applied regardless of gitignore configuration to ensure
common build artifacts and version control directories are excluded.
"""


@dataclass(frozen=True, slots=True)
class IgnoreConfig:
    """Configuration for ignore pattern loading.

    Attributes:
        include_defaults: Whether to include DEFAULT_IGNORE_PATTERNS.
        worktree_gitignore: Whether to load patterns from worktree .gitignore.
        oaps_gitignore: Whether to load patterns from .oaps/.gitignore.
        extra_patterns: Additional patterns to include.
    """

    include_defaults: bool = True
    worktree_gitignore: bool = True
    oaps_gitignore: bool = True
    extra_patterns: tuple[str, ...] = field(default_factory=tuple)


def load_gitignore_patterns(path: Path) -> list[str]:
    """Load patterns from a gitignore file.

    Reads a gitignore-format file and returns the patterns. Comments (lines
    starting with #) and empty lines are filtered out.

    Args:
        path: Path to the gitignore file.

    Returns:
        List of patterns from the file. Returns empty list if file doesn't exist.
    """
    if not path.is_file():
        return []

    patterns: list[str] = []
    content = path.read_text(encoding="utf-8")

    for line in content.splitlines():
        stripped = line.strip()
        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)

    return patterns


def collect_patterns(
    *,
    worktree_root: Path | None = None,
    config: IgnoreConfig | None = None,
) -> list[str]:
    """Collect ignore patterns from all configured sources.

    Gathers patterns from:
    1. Default patterns (if include_defaults is True)
    2. Worktree .gitignore (if worktree_gitignore is True and file exists)
    3. OAPS .gitignore (if oaps_gitignore is True and file exists)
    4. Extra patterns from config

    Args:
        worktree_root: Root directory of the worktree. If None, uses
            get_worktree_root() from oaps.utils._paths.
        config: Configuration for pattern sources. Uses defaults if None.

    Returns:
        List of all collected patterns, deduplicated while preserving order.
    """
    if config is None:
        config = IgnoreConfig()

    patterns: list[str] = []
    seen: set[str] = set()

    def add_patterns(new_patterns: Iterable[str]) -> None:
        for pattern in new_patterns:
            if pattern not in seen:
                seen.add(pattern)
                patterns.append(pattern)

    # Add default patterns first
    if config.include_defaults:
        add_patterns(sorted(DEFAULT_IGNORE_PATTERNS))

    # Resolve worktree root if needed
    if worktree_root is None and (config.worktree_gitignore or config.oaps_gitignore):
        from oaps.utils._paths import get_worktree_root  # noqa: PLC0415

        try:
            worktree_root = get_worktree_root()
        except (FileNotFoundError, OSError):
            # If we can't find worktree (not in git repo), skip file-based patterns
            worktree_root = None

    # Load worktree gitignore
    if config.worktree_gitignore and worktree_root is not None:
        gitignore_path = worktree_root / ".gitignore"
        add_patterns(load_gitignore_patterns(gitignore_path))

    # Load OAPS gitignore
    if config.oaps_gitignore and worktree_root is not None:
        oaps_gitignore_path = worktree_root / ".oaps" / ".gitignore"
        add_patterns(load_gitignore_patterns(oaps_gitignore_path))

    # Add extra patterns
    if config.extra_patterns:
        add_patterns(config.extra_patterns)

    return patterns


def create_pathspec(
    *,
    worktree_root: Path | None = None,
    config: IgnoreConfig | None = None,
) -> PathSpec:
    """Create a PathSpec from collected ignore patterns.

    Args:
        worktree_root: Root directory of the worktree. If None, uses
            get_worktree_root() from oaps.utils._paths.
        config: Configuration for pattern sources. Uses defaults if None.

    Returns:
        A PathSpec instance configured with gitignore-style pattern matching.
    """
    from pathspec import PathSpec as PathSpecClass  # noqa: PLC0415
    from pathspec.patterns.gitwildmatch import GitWildMatchPattern  # noqa: PLC0415

    patterns = collect_patterns(worktree_root=worktree_root, config=config)
    return PathSpecClass.from_lines(GitWildMatchPattern, patterns)
