from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

from dulwich.repo import Repo

if TYPE_CHECKING:
    from uuid import UUID


def get_worktree_root() -> Path:
    """Get the root directory of the current Git worktree."""
    repo = Repo.discover()
    # repo.path is bytes, decode to str and convert to Path
    # It may end with '.git' or '.git/' for bare repos, but for worktrees
    # it's the actual working directory path
    path_str = repo.path.decode() if isinstance(repo.path, bytes) else repo.path
    return Path(path_str)


def get_oaps_dir() -> Path:
    """Get the path to the .oaps/ directory in the current Git worktree."""
    return get_worktree_root() / ".oaps"


def get_oaps_log_dir() -> Path:
    """Get the path to the logs/ directory inside .oaps/."""
    return get_oaps_dir() / "logs"


def get_oaps_hooks_log_file() -> Path:
    """Get the path to the hooks log file inside .oaps/logs/."""
    return get_oaps_log_dir() / "hooks.log"


def get_oaps_sessions_log_dir() -> Path:
    """Get the path to the sessions logs/ directory inside .oaps/logs/."""
    return get_oaps_log_dir() / "sessions"


def get_oaps_session_log_file(session_id: str | UUID) -> Path:
    """Get the path to the log file for a specific session.

    Args:
        session_id: The session ID.

    Returns:
        Path to the session log file.
    """
    return get_oaps_sessions_log_dir() / f"{session_id}.log"


def get_oaps_overrides_dir() -> Path:
    """Get the path to the overrides/ directory inside .oaps/."""
    return get_oaps_dir() / "overrides"


def get_oaps_state_db() -> Path:
    """Get the path to the unified state database.

    Returns:
        Path to the state database (.oaps/state.db).
    """
    return get_oaps_dir() / "state.db"


# Alias for backward compatibility with plan
get_oaps_state_file = get_oaps_state_db


def get_oaps_skill_overrides_dir(skill_name: str) -> Path | None:
    """Get the path to a specific skill override directory.

    Returns the path to .oaps/overrides/skills/<skill_name>.
    """
    path = get_oaps_overrides_dir() / "skills" / skill_name
    if not path.is_dir():
        return None
    return path


def is_oaps_shared() -> bool:
    """Check if .oaps is a symlink (shared across multiple worktrees)."""
    oaps_dir = get_oaps_dir()
    return oaps_dir.is_symlink()


def get_package_dir() -> Path:
    """Get the root directory of the installed oaps package."""
    return Path(str(files("oaps")))


def get_templates_dir() -> Path:
    """Get the path to the package's templates/ directory."""
    return get_package_dir() / "templates"


def get_claude_config_dir() -> Path:
    """Get the Claude Code user configuration directory.

    Returns ~/.claude/ which is used by Claude Code on all platforms.
    """
    return Path.home() / ".claude"


def get_project_skill_dir(skill_name: str) -> Path | None:
    """Get the directory for a project skill.

    Project skills are stored in .oaps/claude/skills/<skill_name>.

    Args:
        skill_name: Name of the skill.

    Returns:
        Path to the skill directory, or None if not found.
    """
    skill_dir = get_oaps_dir() / "claude" / "skills" / skill_name
    if skill_dir.is_dir():
        return skill_dir
    return None


def get_project_skills_dir() -> Path:
    """Get the path to project skills directory (.oaps/claude/skills/).

    Returns:
        Path to the skills directory (may not exist yet).
    """
    return get_oaps_dir() / "claude" / "skills"


def get_plans_dir() -> Path:
    """Get the path to plans directory (.oaps/plans/).

    Returns:
        Path to the plans directory (may not exist yet).
    """
    return get_oaps_dir() / "plans"


def get_oaps_cli_log_file() -> Path:
    """Get the path to the CLI log file inside .oaps/logs/.

    Returns:
        Path to the CLI log file (.oaps/logs/cli.log).
    """
    return get_oaps_log_dir() / "cli.log"
