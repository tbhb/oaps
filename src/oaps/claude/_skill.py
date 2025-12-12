"""Utilities for working with Claude Code skills."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from oaps.utils import get_oaps_dir


def is_project_skill(skill_dir: Path) -> bool:
    """Check if a skill directory is a project skill.

    Args:
        skill_dir: Path to the skill directory.

    Returns:
        True if the skill is from the project location, False if from plugin.
    """
    project_skills_dir = get_oaps_dir() / "claude" / "skills"
    try:
        _ = skill_dir.relative_to(project_skills_dir)
    except ValueError:
        return False
    else:
        return True
