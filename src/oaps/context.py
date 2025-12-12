"""Shared context and utilities for skills, references, and workflows."""

# ruff: noqa: PLC0415

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


class AgentContext(TypedDict):
    """Context information for agents."""

    tool_versions: dict[str, str | None]


class CommandContext(TypedDict):
    """Context information for commands."""

    tool_versions: dict[str, str | None]


class SkillContext(TypedDict):
    """Context information for skills."""

    tool_versions: dict[str, str | None]


@dataclass(slots=True, frozen=True)
class SkillLocation:
    """Resolved location of a skill.

    Attributes:
        skill_dir: Path to the skill directory.
        override_dir: Path to the override directory (for framework skills), or None.
    """

    skill_dir: Path
    override_dir: Path | None


def get_skill_dir(
    skill_name: str,
    *,
    plugin: bool = False,
    project: bool = False,
) -> Path | None:
    """Resolve skill directory based on type.

    Args:
        skill_name: Name of the skill to resolve.
        plugin: If True, search plugin skills.
        project: If True, search project skills.

    When neither flag is specified, searches project first, then falls
    back to plugin. When only one flag is specified, searches only that
    location.

    Returns:
        Path to the skill directory, or None if not found.

    Raises:
        ValueError: If both plugin and project are True.
    """
    from oaps.utils._paths import get_oaps_dir

    if plugin and project:
        msg = "Cannot specify both plugin and project"
        raise ValueError(msg)

    # Determine search mode
    search_both = not plugin and not project
    search_project = project or search_both
    search_plugin = plugin or search_both

    # Try project first if included in search
    if search_project:
        skill_dir = get_oaps_dir() / "claude" / "skills" / skill_name
        if skill_dir.is_dir():
            return skill_dir

    # Try plugin if included in search
    if search_plugin:
        from oaps.utils._claude_plugin import get_claude_plugin_skill_dir

        return get_claude_plugin_skill_dir(skill_name)

    return None


def get_skill_override_dir(skill_name: str) -> Path | None:
    """Get override directory for a framework skill.

    Args:
        skill_name: Name of the skill.

    Returns:
        Path to the override directory, or None if not found.
    """
    from oaps.utils._paths import get_oaps_skill_overrides_dir

    return get_oaps_skill_overrides_dir(skill_name)


def extract_string_list(frontmatter: Mapping[str, object], key: str) -> list[str]:
    """Extract a list of strings from frontmatter.

    Args:
        frontmatter: The parsed frontmatter mapping.
        key: The key to extract.

    Returns:
        List of strings, empty if key not found or not a list.
    """
    raw = frontmatter.get(key)
    if not isinstance(raw, list):
        return []
    typed_list = cast("list[object]", raw)
    return [str(item) for item in typed_list]


def extract_string_dict(frontmatter: Mapping[str, object], key: str) -> dict[str, str]:
    """Extract a dict of strings from frontmatter.

    Args:
        frontmatter: The parsed frontmatter mapping.
        key: The key to extract.

    Returns:
        Dict mapping string keys to string values, empty if not found.
    """
    raw = frontmatter.get(key)
    if not isinstance(raw, dict):
        return {}
    typed_dict = cast("dict[str, object]", raw)
    return {str(k): str(v) for k, v in typed_dict.items()}
