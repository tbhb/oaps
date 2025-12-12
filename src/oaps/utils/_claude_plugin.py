import subprocess
from pathlib import Path
from typing import cast

from ._json import load_json_file
from ._paths import get_claude_config_dir, get_worktree_root


def _get_claude_plugin_marketplaces() -> dict[str, object] | None:
    """Load the known_marketplaces.json file for Claude Code plugins.

    Returns:
        The parsed JSON data as a dictionary, or None if the file cannot be read.
    """
    known_marketplaces = get_claude_config_dir() / "plugins" / "known_marketplaces.json"
    if not known_marketplaces.is_file():
        return None

    data = load_json_file(known_marketplaces)
    if isinstance(data, dict):
        return data
    return None


def get_claude_plugin_dir() -> Path | None:
    """Get the directory where the oaps Claude plugin is installed.

    Reads the Claude Code known_marketplaces.json to find the oaps plugin
    install location. Works for both production installs (from marketplace)
    and development installs (local directory source).

    Returns:
        Path to the oaps plugin directory, or None if not found.
    """
    plugin_marketplaces = _get_claude_plugin_marketplaces()
    if not isinstance(plugin_marketplaces, dict):
        return None

    oaps_entry = plugin_marketplaces.get("oaps")
    if not isinstance(oaps_entry, dict):
        return None

    oaps_dict = cast("dict[str, object]", oaps_entry)
    install_location = oaps_dict.get("installLocation")
    if not isinstance(install_location, str):
        return None

    path = Path(install_location)
    if not path.is_dir():
        return None

    return path


def get_claude_plugin_agents_dir() -> Path | None:
    """Get the agents/ directory inside the oaps Claude plugin directory.

    Returns:
        Path to the agents/ directory, or None if the plugin directory is not found.
    """
    plugin_dir = get_claude_plugin_dir()
    if plugin_dir is None:
        return None

    return plugin_dir / "agents"


def get_claude_plugin_commands_dir() -> Path | None:
    """Get the commands/ directory inside the oaps Claude plugin directory.

    Returns:
        Path to the commands/ directory, or None if the plugin directory is not found.
    """
    plugin_dir = get_claude_plugin_dir()
    if plugin_dir is None:
        return None

    return plugin_dir / "commands"


def get_claude_plugin_skills_dir() -> Path | None:
    """Get the skills/ directory inside the oaps Claude plugin directory.

    Returns:
        Path to the skills/ directory, or None if the plugin directory is not found.
    """
    plugin_dir = get_claude_plugin_dir()
    if plugin_dir is None:
        return None

    return plugin_dir / "skills"


def get_claude_plugin_skill_dir(skill_name: str) -> Path | None:
    """Get the directory for a specific skill.

    Looks for the skill in the following locations (in order):
    1. The Claude plugin's installed skills/ directory (production)
    2. The current Git worktree's skills/ directory (development)

    Args:
        skill_name: The name of the skill.

    Returns:
        Path to the specific skill directory, or None if not found.
    """
    # First, check the Claude plugin install location
    skills_dir = get_claude_plugin_skills_dir()
    if skills_dir is not None:
        skill_dir = skills_dir / skill_name
        if skill_dir.is_dir():
            return skill_dir

    # Fall back to the repo's skills/ directory (for development)
    try:
        repo_skills_dir = get_worktree_root() / "skills"
        skill_dir = repo_skills_dir / skill_name
        if skill_dir.is_dir():
            return skill_dir
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not in a git repo or git is not installed
        return None

    return None
