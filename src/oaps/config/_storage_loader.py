# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Storage configuration loading with precedence-based merging.

This module provides functions to load storage configuration from various
sources including user config, project config, and local overrides.
"""

from pathlib import Path  # noqa: TC003 - Used at runtime in function parameters
from typing import TYPE_CHECKING, Any

from oaps.config._discovery import find_project_root, get_git_dir, get_user_config_path
from oaps.config._loader import read_toml_file
from oaps.config._models._storage import StorageConfiguration
from oaps.exceptions import ConfigLoadError

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


def _extract_storage_log_level(
    data: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> str | None:
    """Extract log_level from TOML data dictionary.

    Checks [storage] section for log_level setting.

    Args:
        data: Parsed TOML dictionary.

    Returns:
        The log_level string if found, None otherwise.
    """
    if "storage" in data and isinstance(data["storage"], dict):
        storage_section: dict[str, Any] = data["storage"]  # pyright: ignore[reportExplicitAny]
        log_level: Any = storage_section.get("log_level")  # pyright: ignore[reportExplicitAny]
        if isinstance(log_level, str):
            return log_level

    return None


def _load_storage_log_level_from_file(path: Path, current: str) -> str:
    """Load log_level from a config file if it exists and contains a valid value.

    Args:
        path: Path to the config file.
        current: Current log_level value to return if file doesn't exist
            or has no setting.

    Returns:
        The log_level from the file, or current if not found.
    """
    if not path.is_file():
        return current

    try:
        data = read_toml_file(path)
        extracted = _extract_storage_log_level(data)
        if extracted is not None:
            return extracted
    except ConfigLoadError:
        pass

    return current


def load_storage_configuration(
    project_root: Path | None = None,
    logger: FilteringBoundLogger | None = None,
) -> StorageConfiguration:
    """Load storage configuration from all sources.

    Main entry point for storage configuration. Discovers and loads
    configuration from all sources in precedence order, returning
    a StorageConfiguration with the highest-precedence log_level.

    Args:
        project_root: Project root directory. If None, auto-detect
            by searching upward for `.oaps/` directory.
        logger: Optional logger for diagnostics (not currently used but
            included for consistency with hooks loader).

    Returns:
        StorageConfiguration with log_level.

    Sources (lowest to highest precedence for log_level):
        1. Default ("info")
        2. User config (~/.config/oaps/config.toml [storage] log_level)
        3. Project config (.oaps/oaps.toml [storage] log_level)
        4. Local overrides (.oaps/oaps.local.toml [storage] log_level)
        5. Worktree config (.git/oaps.toml [storage] log_level)
    """
    # Suppress unused logger warning - kept for API consistency
    _ = logger

    # Determine log_level from config sources (highest precedence wins)
    log_level: str = "info"  # Default

    resolved_root = project_root if project_root else find_project_root()

    # Check user config
    log_level = _load_storage_log_level_from_file(get_user_config_path(), log_level)

    if resolved_root:
        oaps_dir = resolved_root / ".oaps"

        # Check project config, local overrides, and worktree in precedence order
        log_level = _load_storage_log_level_from_file(oaps_dir / "oaps.toml", log_level)
        log_level = _load_storage_log_level_from_file(
            oaps_dir / "oaps.local.toml", log_level
        )

        git_dir = get_git_dir(resolved_root)
        if git_dir:
            log_level = _load_storage_log_level_from_file(
                git_dir / "oaps.toml", log_level
            )

    # Validate log_level
    valid_levels = {"error", "warning", "info", "debug"}
    if log_level not in valid_levels:
        # Use default if invalid - no logger to warn since it's optional
        log_level = "info"

    return StorageConfiguration(
        log_level=log_level,  # pyright: ignore[reportArgumentType]
    )
