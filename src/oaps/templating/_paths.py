"""Template search path building utilities."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(slots=True, frozen=True)
class TemplateSearchPaths:
    """Result of search path resolution.

    Attributes:
        paths: Ordered tuple of existing directories, highest precedence first.
        namespace: Optional namespace for debugging/logging.
    """

    paths: tuple[Path, ...]
    namespace: str | None = None


@dataclass(slots=True, frozen=True)
class BasePathConfig:
    """Configuration for base paths used in template search.

    Attributes:
        user_base: User config base directory.
            Defaults to platformdirs.user_config_path("oaps").
        project_base: Project base directory. Defaults to get_oaps_dir().
        plugin_base: Plugin base directory. Defaults to get_claude_plugin_dir().
        extra_paths: Additional explicit paths (added first, highest precedence).
    """

    user_base: Path | None = None
    project_base: Path | None = None
    plugin_base: Path | None = None
    extra_paths: tuple[Path, ...] = field(default_factory=tuple)


def _resolve_pattern(
    pattern: str,
    variables: dict[str, str],
    base: Path,
) -> Path | None:
    """Resolve a single pattern with the given base and variables.

    Args:
        pattern: Path pattern with {base} and other placeholders.
        variables: Variables to substitute in the pattern.
        base: Base path to use for {base} placeholder.

    Returns:
        Resolved path if it exists as a directory, None otherwise.
    """
    full_vars = {"base": str(base), **variables}

    try:
        resolved_str = pattern.format_map(full_vars)
    except KeyError:
        return None

    resolved_path = Path(resolved_str)
    return resolved_path if resolved_path.is_dir() else None


def _get_default_bases() -> tuple[Path | None, Path | None, Path | None]:
    """Get default base paths for user, project, and plugin.

    Returns:
        Tuple of (user_base, project_base, plugin_base).
    """
    import platformdirs  # noqa: PLC0415

    from oaps.utils._claude_plugin import get_claude_plugin_dir  # noqa: PLC0415
    from oaps.utils._paths import get_oaps_dir  # noqa: PLC0415

    user_base = platformdirs.user_config_path("oaps")

    try:
        project_base: Path | None = get_oaps_dir()
    except (OSError, RuntimeError):
        project_base = None

    plugin_base = get_claude_plugin_dir()

    return user_base, project_base, plugin_base


def _collect_valid_bases(config: BasePathConfig) -> list[Path]:
    """Collect valid base paths from config, applying defaults.

    Args:
        config: Base path configuration.

    Returns:
        List of valid base paths in precedence order.
    """
    default_user, default_project, default_plugin = _get_default_bases()

    bases: list[Path] = []

    user_base = config.user_base if config.user_base is not None else default_user
    if user_base is not None and user_base.is_dir():
        bases.append(user_base)

    project_base = (
        config.project_base if config.project_base is not None else default_project
    )
    if project_base is not None and project_base.is_dir():
        bases.append(project_base)

    plugin_base = (
        config.plugin_base if config.plugin_base is not None else default_plugin
    )
    if plugin_base is not None and plugin_base.is_dir():
        bases.append(plugin_base)

    return bases


def _add_unique_path(
    path: Path,
    result_paths: list[Path],
    seen: set[Path],
) -> None:
    """Add a path to results if not already seen.

    Args:
        path: Path to add.
        result_paths: List to append to.
        seen: Set of already-seen paths.
    """
    resolved = path.resolve()
    if resolved not in seen:
        seen.add(resolved)
        result_paths.append(resolved)


def build_search_paths(
    patterns: Sequence[str],
    variables: dict[str, str],
    *,
    config: BasePathConfig | None = None,
) -> TemplateSearchPaths:
    """Build template search paths from patterns.

    For each pattern, tries formatting with each base path and the provided variables.
    Only includes paths that exist as directories. Deduplicates while preserving order.

    Patterns should use {base} for the base directory placeholder, plus any
    subsystem-specific variables like {namespace}, {name}, etc.

    The base paths are tried in order of precedence:
    1. user_base (highest precedence - user overrides)
    2. project_base (project-specific customizations)
    3. plugin_base (plugin defaults, lowest precedence)

    If any base path is None, it defaults to:
    - user_base: platformdirs.user_config_path("oaps")
    - project_base: get_oaps_dir()
    - plugin_base: get_claude_plugin_dir()

    Args:
        patterns: Path patterns in precedence order (highest first).
        variables: Variables to substitute in patterns (e.g., {"namespace": "dev"}).
        config: Optional base path configuration. If None, uses defaults for all bases.

    Returns:
        TemplateSearchPaths with resolved paths.

    Example:
        paths = build_search_paths(
            patterns=[
                "{base}/overrides/flows/{namespace}/_templates",
                "{base}/flows/{namespace}/_templates",
                "{base}/flows/_templates",
            ],
            variables={"namespace": "dev"},
        )
    """
    if config is None:
        config = BasePathConfig()

    bases = _collect_valid_bases(config)

    result_paths: list[Path] = []
    seen: set[Path] = set()

    # Add extra paths first (highest precedence)
    for path in config.extra_paths:
        if path.is_dir():
            _add_unique_path(path, result_paths, seen)

    # For each pattern, try each base in precedence order
    for pattern in patterns:
        for base in bases:
            resolved = _resolve_pattern(pattern, variables, base)
            if resolved is not None:
                _add_unique_path(resolved, result_paths, seen)

    return TemplateSearchPaths(
        paths=tuple(result_paths),
        namespace=variables.get("namespace"),
    )
