"""Project root and config path discovery utilities.

This module provides functions for locating the OAPS project root
by searching upward through the directory tree for the `.oaps/` marker directory,
and for determining platform-specific configuration file paths.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import platformdirs

from ._defaults import DEFAULT_CONFIG
from ._models._common import ConfigSource, ConfigSourceName

if TYPE_CHECKING:
    from dulwich.repo import Repo


def find_project_root(start: Path | None = None) -> Path | None:
    """Find the project root by searching upward for .oaps/ directory.

    Searches from the starting directory upward through parent directories
    until a directory containing `.oaps/` is found, or the filesystem root
    is reached.

    Args:
        start: Directory to start searching from. Defaults to current
            working directory if not specified.

    Returns:
        Path to the project root directory (the directory containing `.oaps/`),
        or None if no project root is found.

    Examples:
        >>> # Find project root from current directory
        >>> root = find_project_root()
        >>> # Find project root from specific directory
        >>> root = find_project_root(Path("/path/to/subdir"))
    """
    current = (start or Path.cwd()).resolve()

    while True:
        if (current / ".oaps").is_dir():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            return None
        current = parent


def get_user_config_path() -> Path:
    r"""Get platform-specific user config file path.

    Returns the path to the user's OAPS configuration file, using
    the platform-appropriate location:

    - Linux: ``~/.config/oaps/config.toml``
    - macOS: ``~/Library/Application Support/oaps/config.toml``
    - Windows: ``%APPDATA%\oaps\config.toml``

    The path is returned regardless of whether the file or parent
    directory exists. Callers are responsible for creating the
    directory if needed.

    Returns:
        Path to the user config file for the current platform.

    Examples:
        >>> # Get user config path
        >>> path = get_user_config_path()
        >>> path.name
        'config.toml'
        >>> path.parent.name
        'oaps'
    """
    config_dir = platformdirs.user_config_path("oaps")
    return config_dir / "config.toml"


def get_git_dir(path: Path | None = None) -> Path | None:
    """Get the .git directory for the given path.

    This function finds the git directory for a repository, handling both
    regular repositories and linked worktrees correctly. For linked worktrees,
    it returns the worktree-specific git directory (e.g., `.git/worktrees/<name>/`),
    not the main `.git/` directory.

    Args:
        path: Directory to start searching from. Defaults to current
            working directory if not specified.

    Returns:
        Path to the .git directory, or None if not in a git repository.

    Examples:
        >>> # Find git directory from current directory
        >>> git_dir = get_git_dir()
        >>> # Find git directory from specific path
        >>> git_dir = get_git_dir(Path("/path/to/repo"))
    """
    from dulwich.errors import NotGitRepository  # noqa: PLC0415
    from dulwich.repo import Repo  # noqa: PLC0415

    search_path = str(path.resolve()) if path else "."

    try:
        repo: Repo = Repo.discover(search_path)
        # repo.path returns the .git directory path
        return Path(repo.path)
    except NotGitRepository:
        return None


def _file_exists(path: Path) -> bool:
    """Check if a file exists, handling permission errors gracefully.

    Args:
        path: Path to check.

    Returns:
        True if the file exists and is accessible, False otherwise.
    """
    try:
        return path.is_file()
    except OSError:
        return False


def discover_sources(
    project_root: Path | None = None,
    *,
    include_env: bool = True,
    include_cli: bool = False,
    cli_overrides: dict[str, Any] | None = None,  # pyright: ignore[reportExplicitAny]
) -> list[ConfigSource]:
    """Discover all configuration sources.

    Discovers configuration sources in precedence order (highest first).
    File-based sources are checked for existence. Sources that depend on
    a project root are omitted if no project root is found.

    Args:
        project_root: Project root directory. If None, auto-detect by
            searching upward for `.oaps/` directory.
        include_env: Include environment variables as a source.
        include_cli: Include CLI overrides as a source.
        cli_overrides: Dictionary of CLI argument overrides. Only used
            if include_cli is True.

    Returns:
        List of ConfigSource objects in precedence order (highest first).
        Sources that don't exist are still included with exists=False.

    Examples:
        >>> # Discover all sources in current project
        >>> sources = discover_sources()
        >>> # Discover sources with explicit project root
        >>> sources = discover_sources(Path("/path/to/project"))
        >>> # Include CLI overrides
        >>> overrides = {"logging": {"level": "debug"}}
        >>> sources = discover_sources(include_cli=True, cli_overrides=overrides)
    """
    sources: list[ConfigSource] = []

    # Resolve project root
    resolved_root = project_root if project_root else find_project_root()

    # 1. CLI source (highest precedence)
    if include_cli:
        sources.append(
            ConfigSource(
                name=ConfigSourceName.CLI,
                path=None,
                exists=bool(cli_overrides),
                values=cli_overrides or {},
            )
        )

    # 2. ENV source
    if include_env:
        sources.append(
            ConfigSource(
                name=ConfigSourceName.ENV,
                path=None,
                exists=True,  # Actual values parsed during loading phase
                values={},
            )
        )

    # Project-dependent sources (only if we have a project root)
    if resolved_root:
        # 3. Worktree config
        git_dir = get_git_dir(resolved_root)
        if git_dir:
            worktree_path = git_dir / "oaps.toml"
            sources.append(
                ConfigSource(
                    name=ConfigSourceName.WORKTREE,
                    path=worktree_path,
                    exists=_file_exists(worktree_path),
                    values={},
                )
            )

        # 4. Local config
        local_path = resolved_root / ".oaps" / "oaps.local.toml"
        sources.append(
            ConfigSource(
                name=ConfigSourceName.LOCAL,
                path=local_path,
                exists=_file_exists(local_path),
                values={},
            )
        )

        # 5. Project config
        project_path = resolved_root / ".oaps" / "oaps.toml"
        sources.append(
            ConfigSource(
                name=ConfigSourceName.PROJECT,
                path=project_path,
                exists=_file_exists(project_path),
                values={},
            )
        )

    # 6. User config (always included, does not depend on project)
    user_path = get_user_config_path()
    sources.append(
        ConfigSource(
            name=ConfigSourceName.USER,
            path=user_path,
            exists=_file_exists(user_path),
            values={},
        )
    )

    # 7. Default config (lowest precedence, always exists)
    sources.append(
        ConfigSource(
            name=ConfigSourceName.DEFAULT,
            path=None,
            exists=True,
            values=DEFAULT_CONFIG,
        )
    )

    return sources
