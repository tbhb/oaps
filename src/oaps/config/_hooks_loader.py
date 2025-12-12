# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Hook rule loading from multiple sources with precedence-based merging.

This module provides functions to discover, load, and merge hook rules from
various configuration sources including built-in rules, user config, project
config, drop-in files, and worktree overrides.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from oaps.config._discovery import find_project_root, get_git_dir, get_user_config_path
from oaps.config._loader import read_toml_file
from oaps.config._models._hooks import HookRuleConfiguration, HooksConfiguration
from oaps.exceptions import ConfigLoadError
from oaps.utils._logging import create_hooks_logger
from oaps.utils._paths import get_package_dir

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


def discover_drop_in_files(directory: Path) -> list[Path]:
    """Find all *.toml files in directory, sorted lexicographically.

    Args:
        directory: Directory to search for drop-in files.

    Returns:
        List of Path objects to .toml files, sorted by filename.
        Empty list if directory doesn't exist.
    """
    if not directory.is_dir():
        return []

    files = list(directory.glob("*.toml"))
    return sorted(files, key=lambda p: p.name)


def _get_dropin_dir(project_root: Path) -> Path:
    """Get drop-in directory, respecting OAPS_HOOKS__DROPIN_DIR env var.

    Args:
        project_root: Project root directory.

    Returns:
        Path to drop-in directory.
    """
    env_override = os.environ.get("OAPS_HOOKS__DROPIN_DIR", "").strip()
    if env_override:
        override_path = Path(env_override)
        if override_path.is_absolute():
            return override_path
        return project_root / override_path
    return project_root / ".oaps" / "hooks.d"


def _get_builtin_hooks_dir() -> Path:
    """Get path to built-in hooks directory in oaps package.

    Returns the path to the `hooks/builtin/` directory within the oaps package,
    which contains default hook rule TOML files shipped with OAPS.
    """
    return get_package_dir() / "hooks" / "builtin"


def _load_rules_from_toml(
    data: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    source_file: Path,
    logger: FilteringBoundLogger,
    *,
    warn_on_non_rules: bool = False,
) -> list[HookRuleConfiguration]:
    """Parse rules from TOML data dictionary.

    Accepts both [[rules]] (for drop-in files) and [[hooks.rules]]
    (for main config files) sections.

    Args:
        data: Parsed TOML dictionary.
        source_file: Path to the source file for tracking.
        logger: Logger for validation warnings.
        warn_on_non_rules: If True, warn about non-rules sections.

    Returns:
        List of HookRuleConfiguration objects.
    """
    result: list[HookRuleConfiguration] = []

    # Extract rules from [[rules]] or [[hooks.rules]]
    rules_data: Any = []  # pyright: ignore[reportExplicitAny]

    if "rules" in data:
        rules_data = data.get("rules", [])
        if warn_on_non_rules:
            unexpected_keys = set(data.keys()) - {"rules"}
            if unexpected_keys:
                logger.warning(
                    "Drop-in file contains non-rules sections (ignored)",
                    file=source_file.name,
                    unexpected_keys=sorted(unexpected_keys),
                )
    elif "hooks" in data and isinstance(data["hooks"], dict):
        hooks_section: dict[str, Any] = data["hooks"]  # pyright: ignore[reportExplicitAny]
        rules_data = hooks_section.get("rules", [])

    if not isinstance(rules_data, list):
        logger.warning(
            "Rules section is not a list",
            file=source_file.name,
        )
        return result

    for i, rule_data in enumerate(rules_data):
        if not isinstance(rule_data, dict):
            logger.warning(
                "Rule entry is not a dictionary",
                file=source_file.name,
                index=i,
            )
            continue

        try:
            # Add source tracking field before validation
            rule_data_with_source: dict[str, Any] = {  # pyright: ignore[reportExplicitAny]
                **rule_data,
                "source_file": source_file,
            }
            rule = HookRuleConfiguration.model_validate(rule_data_with_source)
            result.append(rule)
        except ValidationError as e:
            typed_rule_data: dict[str, Any] = rule_data  # pyright: ignore[reportExplicitAny]
            rule_id: str = typed_rule_data.get("id", f"<index {i}>")
            logger.warning(
                "Invalid rule configuration (skipped)",
                file=source_file.name,
                rule_id=rule_id,
                error=str(e),
            )

    return result


def _extract_log_level(
    data: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> str | None:
    """Extract log_level from TOML data dictionary.

    Checks both [hooks] section (for config files) and top-level (for drop-in files).

    Args:
        data: Parsed TOML dictionary.

    Returns:
        The log_level string if found, None otherwise.
    """
    # Check [[hooks]] section first (for main config files)
    if "hooks" in data and isinstance(data["hooks"], dict):
        hooks_section: dict[str, Any] = data["hooks"]  # pyright: ignore[reportExplicitAny]
        log_level: Any = hooks_section.get("log_level")  # pyright: ignore[reportExplicitAny]
        if isinstance(log_level, str):
            return log_level

    # Check top-level (for drop-in files or simplified config)
    top_level_log_level: Any = data.get("log_level")  # pyright: ignore[reportExplicitAny]
    if isinstance(top_level_log_level, str):
        return top_level_log_level

    return None


def load_drop_in_rules(
    directory: Path,
    logger: FilteringBoundLogger | None = None,
) -> list[HookRuleConfiguration]:
    """Load rules from all drop-in files in a directory.

    Args:
        directory: Directory containing drop-in .toml files.
        logger: Optional logger for diagnostics.

    Returns:
        List of HookRuleConfiguration objects from all files.
        Rules maintain order: files processed lexicographically,
        rules within each file maintain definition order.
        Each rule has source_file set to its originating file.

    Note:
        - Files that fail to parse are logged and skipped (fail-open)
        - Non-rules sections in files generate warnings but don't fail
    """
    if logger is None:
        logger = create_hooks_logger()

    files = discover_drop_in_files(directory)
    result: list[HookRuleConfiguration] = []

    for path in files:
        try:
            data = read_toml_file(path)
            rules = _load_rules_from_toml(data, path, logger, warn_on_non_rules=True)
            result.extend(rules)
        except ConfigLoadError as e:
            logger.warning(
                "Failed to parse drop-in file (skipped)",
                file=path.name,
                error=str(e),
            )
        except FileNotFoundError:
            # File was deleted between discovery and reading
            pass

    return result


def _load_rules_from_file(
    path: Path,
    logger: FilteringBoundLogger,
    *,
    warn_on_non_rules: bool = False,
) -> list[HookRuleConfiguration]:
    """Load rules from a single file if it exists.

    Args:
        path: Path to the config file.
        logger: Logger for diagnostics.
        warn_on_non_rules: If True, warn on non-rules sections.

    Returns:
        List of HookRuleConfiguration objects, empty if file doesn't exist.
    """
    if not path.is_file():
        return []

    try:
        data = read_toml_file(path)
        return _load_rules_from_toml(
            data, path, logger, warn_on_non_rules=warn_on_non_rules
        )
    except ConfigLoadError as e:
        logger.warning(
            "Failed to parse config file (skipped)",
            file=path.name,
            error=str(e),
        )
        return []


def merge_hook_rules(
    *rule_lists: list[HookRuleConfiguration],
) -> list[HookRuleConfiguration]:
    """Merge multiple rule lists with ID-based deduplication.

    Rules are processed in order. When multiple rules share the same ID,
    the last one (highest precedence) wins.

    Args:
        *rule_lists: Rule lists in precedence order (lowest first).

    Returns:
        Merged list with later rules overriding earlier ones by ID.
        Order preserved: rules appear in first-seen order, but
        properties come from highest-precedence source.
    """
    # Use dict to track latest rule per ID, preserving insertion order
    rules_by_id: dict[str, HookRuleConfiguration] = {}

    for rule_list in rule_lists:
        for rule in rule_list:
            rules_by_id[rule.id] = rule

    # Return rules in insertion order (first-seen order)
    return list(rules_by_id.values())


def load_all_hook_rules(
    project_root: Path | None = None,
    logger: FilteringBoundLogger | None = None,
) -> list[HookRuleConfiguration]:
    """Load and merge hook rules from all sources.

    Main entry point for hook configuration. Discovers and loads
    rules from all sources in precedence order, returning the
    merged result.

    Args:
        project_root: Project root directory. If None, auto-detect
            by searching upward for `.oaps/` directory.
        logger: Optional logger for diagnostics.

    Returns:
        Merged list of HookRuleConfiguration objects.

    Sources (lowest to highest precedence):
        1. Built-in hooks (<oaps_package>/hooks/builtin/*.toml)
        2. User config inline rules (~/.config/oaps/config.toml [[hooks.rules]])
        3. Project hooks.toml (.oaps/hooks.toml)
        4. Project drop-in files (.oaps/hooks.d/*.toml, lexicographic order)
        5. Project inline rules (.oaps/oaps.toml [[hooks.rules]])
        6. Local overrides (.oaps/oaps.local.toml [[hooks.rules]])
        7. Worktree config (.git/oaps.toml [[hooks.rules]])

    Environment Variables:
        OAPS_HOOKS__DROPIN_DIR: Override drop-in directory path
    """
    if logger is None:
        logger = create_hooks_logger()

    # Collect rules from each source in precedence order (lowest first)
    builtin_rules: list[HookRuleConfiguration] = []
    user_rules: list[HookRuleConfiguration] = []
    project_external_rules: list[HookRuleConfiguration] = []
    dropin_rules: list[HookRuleConfiguration] = []
    project_inline_rules: list[HookRuleConfiguration] = []
    local_rules: list[HookRuleConfiguration] = []
    worktree_rules: list[HookRuleConfiguration] = []

    # Resolve project root
    resolved_root = project_root if project_root else find_project_root()

    # 1. Built-in hooks (lowest precedence)
    builtin_dir = _get_builtin_hooks_dir()
    if builtin_dir.is_dir():
        builtin_rules = load_drop_in_rules(builtin_dir, logger)

    # 2. User config inline rules
    user_config_path = get_user_config_path()
    user_rules = _load_rules_from_file(user_config_path, logger)

    # Project-dependent sources
    if resolved_root:
        oaps_dir = resolved_root / ".oaps"

        # 3. Project external hooks file
        hooks_file = oaps_dir / "hooks.toml"
        project_external_rules = _load_rules_from_file(hooks_file, logger)

        # 4. Project drop-in files
        dropin_dir = _get_dropin_dir(resolved_root)
        dropin_rules = load_drop_in_rules(dropin_dir, logger)

        # 5. Project inline rules
        project_config = oaps_dir / "oaps.toml"
        project_inline_rules = _load_rules_from_file(project_config, logger)

        # 6. Local overrides
        local_config = oaps_dir / "oaps.local.toml"
        local_rules = _load_rules_from_file(local_config, logger)

        # 7. Worktree config (highest precedence)
        git_dir = get_git_dir(resolved_root)
        if git_dir:
            worktree_config = git_dir / "oaps.toml"
            worktree_rules = _load_rules_from_file(worktree_config, logger)

    return merge_hook_rules(
        builtin_rules,
        user_rules,
        project_external_rules,
        dropin_rules,
        project_inline_rules,
        local_rules,
        worktree_rules,
    )


def _load_log_level_from_file(path: Path, current: str) -> str:
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
        extracted = _extract_log_level(data)
        if extracted is not None:
            return extracted
    except ConfigLoadError:
        pass

    return current


def load_hooks_configuration(
    project_root: Path | None = None,
    logger: FilteringBoundLogger | None = None,
) -> HooksConfiguration:
    """Load complete hooks configuration from all sources.

    Main entry point for hook configuration. Discovers and loads
    configuration from all sources in precedence order, returning
    a HooksConfiguration with merged rules and highest-precedence log_level.

    Args:
        project_root: Project root directory. If None, auto-detect
            by searching upward for `.oaps/` directory.
        logger: Optional logger for diagnostics.

    Returns:
        HooksConfiguration with merged rules and log_level.

    Sources (lowest to highest precedence for log_level):
        1. Default ("info")
        2. User config (~/.config/oaps/config.toml [hooks] log_level)
        3. Project config (.oaps/oaps.toml [hooks] log_level)
        4. Local overrides (.oaps/oaps.local.toml [hooks] log_level)
        5. Worktree config (.git/oaps.toml [hooks] log_level)

    Note:
        Rules are loaded via load_all_hook_rules with full precedence chain.
        log_level uses a simpler precedence: highest-precedence source wins.
    """
    if logger is None:
        logger = create_hooks_logger()

    # Load merged rules
    rules = load_all_hook_rules(project_root, logger)

    # Determine log_level from config sources (highest precedence wins)
    log_level: str = "info"  # Default

    resolved_root = project_root if project_root else find_project_root()

    # Check user config
    log_level = _load_log_level_from_file(get_user_config_path(), log_level)

    if resolved_root:
        oaps_dir = resolved_root / ".oaps"

        # Check project config, local overrides, and worktree in precedence order
        log_level = _load_log_level_from_file(oaps_dir / "oaps.toml", log_level)
        log_level = _load_log_level_from_file(oaps_dir / "oaps.local.toml", log_level)

        git_dir = get_git_dir(resolved_root)
        if git_dir:
            log_level = _load_log_level_from_file(git_dir / "oaps.toml", log_level)

    # Validate log_level
    valid_levels = {"error", "warning", "info", "debug"}
    if log_level not in valid_levels:
        logger.warning(
            "Invalid hooks.log_level, using default",
            configured_level=log_level,
            default_level="info",
        )
        log_level = "info"

    return HooksConfiguration(
        log_level=log_level,  # pyright: ignore[reportArgumentType]
        rules=rules,
    )
