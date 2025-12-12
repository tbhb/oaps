"""OAPS expression function implementations.

This module provides custom functions that can be called in hook condition
expressions. Each function is implemented as a frozen dataclass with a
__call__ method for clean testability.

Note: Parameters are typed as `object` because rule-engine may pass values
of unexpected types at runtime. Each function validates input types and
returns a safe default value for invalid inputs.
"""

import os
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.project import Project
    from oaps.session import Session
    from oaps.utils import GitContext


@dataclass(frozen=True, slots=True)
class IsPathUnderFunction:
    """Check if path is safely under base directory.

    Expression usage: $is_path_under(path, base)

    Uses Path.resolve() and is_relative_to() for secure path checking,
    preventing path traversal attacks.
    """

    def __call__(self, path: object, base: object) -> bool:
        """Check if path is under base directory.

        Args:
            path: Path to check.
            base: Base directory path.

        Returns:
            True if path is under base, False otherwise.
        """
        if not isinstance(path, str) or not isinstance(base, str):
            return False
        try:
            resolved_path = Path(path).resolve(strict=False)
            resolved_base = Path(base).resolve(strict=False)
            return resolved_path.is_relative_to(resolved_base)
        except (ValueError, OSError):
            return False


@dataclass(frozen=True, slots=True)
class FileExistsFunction:
    """Check if file exists.

    Expression usage: $file_exists(path)
    """

    def __call__(self, path: object) -> bool:
        """Check if file exists at the given path.

        Args:
            path: Path to check.

        Returns:
            True if file exists, False otherwise.
        """
        if not isinstance(path, str):
            return False
        try:
            return Path(path).exists()
        except OSError:
            return False


@dataclass(frozen=True, slots=True)
class IsExecutableFunction:
    """Check if file is executable.

    Expression usage: $is_executable(path)
    """

    def __call__(self, path: object) -> bool:
        """Check if file is executable.

        Args:
            path: Path to check.

        Returns:
            True if file exists and is executable, False otherwise.
        """
        if not isinstance(path, str):
            return False
        try:
            p = Path(path)
            return p.is_file() and os.access(p, os.X_OK)
        except OSError:
            return False


@dataclass(frozen=True, slots=True)
class MatchesGlobFunction:
    """Check if path matches glob pattern.

    Expression usage: $matches_glob(path, pattern)
    """

    def __call__(self, path: object, pattern: object) -> bool:
        """Check if path matches the glob pattern.

        Args:
            path: Path to check.
            pattern: Glob pattern to match against.

        Returns:
            True if path matches pattern, False otherwise.
        """
        if not isinstance(path, str) or not isinstance(pattern, str):
            return False
        return fnmatch(path, pattern)


@dataclass(frozen=True, slots=True)
class EnvFunction:
    """Get environment variable value.

    Expression usage: $env(name)
    """

    def __call__(self, name: object) -> str | None:
        """Get value of environment variable.

        Args:
            name: Environment variable name.

        Returns:
            The environment variable value, or None if not set.
        """
        if not isinstance(name, str):
            return None
        return os.environ.get(name)


@dataclass(frozen=True, slots=True)
class IsGitRepoFunction:
    """Check if cwd is inside a git repository.

    Expression usage: $is_git_repo()

    This function is bound to a specific working directory at creation time.
    """

    cwd: str

    def __call__(self) -> bool:
        """Check if cwd is inside a git repository.

        Walks up the directory tree looking for a .git directory.

        Returns:
            True if inside a git repository, False otherwise.
        """
        try:
            p = Path(self.cwd)
            return any((parent / ".git").exists() for parent in [p, *p.parents])
        except OSError:
            return False


@dataclass(frozen=True, slots=True)
class SessionGetFunction:
    """Get value from session store.

    Expression usage: $session_get(key)

    This function is bound to a specific Session at creation time.
    """

    session: Session

    def __call__(self, key: object) -> str | int | float | bytes | None:
        """Get value from session store.

        Args:
            key: Key to look up.

        Returns:
            The stored value, or None if not found.
        """
        if not isinstance(key, str):
            return None
        return self.session.get(key)


@dataclass(frozen=True, slots=True)
class ProjectGetFunction:
    """Get value from project state store.

    Expression usage: $project_get(key)

    This function is bound to a specific Project at creation time.
    Follows fail-open semantics: errors return None and log a warning.
    """

    project: Project | None

    def __call__(self, key: object) -> str | int | float | bytes | None:
        """Get value from project state store.

        Args:
            key: Key to look up.

        Returns:
            The stored value, or None if not found or on error.
        """
        import logging  # noqa: PLC0415
        import sqlite3  # noqa: PLC0415

        if not isinstance(key, str):
            return None
        if self.project is None:
            return None
        try:
            return self.project.get(key)
        except (OSError, sqlite3.Error):
            logging.getLogger(__name__).warning(
                "Error accessing project state for key '%s'", key, exc_info=True
            )
            return None


# ---------------------------------------------------------------------------
# Git-related expression functions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IsStagedFunction:
    """Check if a file is staged.

    Expression usage: $is_staged(path)

    This function is bound to the staged files set at creation time.
    """

    staged_files: frozenset[str]

    def __call__(self, path: object) -> bool:
        """Check if a file is staged.

        Args:
            path: Repository-relative file path to check.

        Returns:
            True if file is staged, False otherwise.
        """
        if not isinstance(path, str):
            return False
        return path in self.staged_files


@dataclass(frozen=True, slots=True)
class IsModifiedFunction:
    """Check if a file is modified (unstaged).

    Expression usage: $is_modified(path)

    This function is bound to the modified files set at creation time.
    """

    modified_files: frozenset[str]

    def __call__(self, path: object) -> bool:
        """Check if a file is modified but unstaged.

        Args:
            path: Repository-relative file path to check.

        Returns:
            True if file is modified, False otherwise.
        """
        if not isinstance(path, str):
            return False
        return path in self.modified_files


@dataclass(frozen=True, slots=True)
class HasConflictsFunction:
    """Check if repository has merge conflicts.

    Expression usage: $has_conflicts()

    This function is bound to the conflict files set at creation time.
    """

    conflict_files: frozenset[str]

    def __call__(self) -> bool:
        """Check if repository has merge conflicts.

        Returns:
            True if there are conflict files, False otherwise.
        """
        return len(self.conflict_files) > 0


@dataclass(frozen=True, slots=True)
class CurrentBranchFunction:
    """Get current branch name.

    Expression usage: $current_branch()

    This function is bound to the branch name at creation time.
    """

    branch: str | None

    def __call__(self) -> str | None:
        """Get current branch name.

        Returns:
            Branch name, or None if HEAD is detached.
        """
        return self.branch


@dataclass(frozen=True, slots=True)
class GitHasStagedFunction:
    """Check if staged files exist, optionally matching a pattern.

    Expression usage: $git_has_staged() or $git_has_staged(pattern)

    This function is bound to the staged files set at creation time.
    """

    staged_files: frozenset[str]

    def __call__(self, pattern: object = None) -> bool:
        """Check if staged files exist, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to match against staged files.

        Returns:
            True if staged files exist (matching pattern if provided), False otherwise.
        """
        if len(self.staged_files) == 0:
            return False
        if pattern is None:
            return True
        if not isinstance(pattern, str):
            return False
        return any(fnmatch(f, pattern) for f in self.staged_files)


@dataclass(frozen=True, slots=True)
class GitHasModifiedFunction:
    """Check if modified files exist, optionally matching a pattern.

    Expression usage: $git_has_modified() or $git_has_modified(pattern)

    This function is bound to the modified files set at creation time.
    """

    modified_files: frozenset[str]

    def __call__(self, pattern: object = None) -> bool:
        """Check if modified files exist, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to match against modified files.

        Returns:
            True if modified files exist (matching pattern if given), False otherwise.
        """
        if len(self.modified_files) == 0:
            return False
        if pattern is None:
            return True
        if not isinstance(pattern, str):
            return False
        return any(fnmatch(f, pattern) for f in self.modified_files)


@dataclass(frozen=True, slots=True)
class GitHasUntrackedFunction:
    """Check if untracked files exist, optionally matching a pattern.

    Expression usage: $git_has_untracked() or $git_has_untracked(pattern)

    This function is bound to the untracked files set at creation time.
    """

    untracked_files: frozenset[str]

    def __call__(self, pattern: object = None) -> bool:
        """Check if untracked files exist, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to match against untracked files.

        Returns:
            True if untracked files exist (matching pattern if given), False otherwise.
        """
        if len(self.untracked_files) == 0:
            return False
        if pattern is None:
            return True
        if not isinstance(pattern, str):
            return False
        return any(fnmatch(f, pattern) for f in self.untracked_files)


@dataclass(frozen=True, slots=True)
class GitHasConflictsFunction:
    """Check if conflict files exist, optionally matching a pattern.

    Expression usage: $git_has_conflicts() or $git_has_conflicts(pattern)

    This function is bound to the conflict files set at creation time.
    """

    conflict_files: frozenset[str]

    def __call__(self, pattern: object = None) -> bool:
        """Check if conflict files exist, optionally matching a pattern.

        Args:
            pattern: Optional glob pattern to match against conflict files.

        Returns:
            True if conflict files exist (matching pattern if given), False otherwise.
        """
        if len(self.conflict_files) == 0:
            return False
        if pattern is None:
            return True
        if not isinstance(pattern, str):
            return False
        return any(fnmatch(f, pattern) for f in self.conflict_files)


@dataclass(frozen=True, slots=True)
class GitFileInFunction:
    """Check if a file is in a specific git status set.

    Expression usage: $git_file_in(path, "staged"|"modified"|"untracked"|"conflict")

    This function is bound to the GitContext at creation time.
    """

    git: GitContext | None

    def __call__(self, path: object, set_name: object) -> bool:
        """Check if a file is in a specific git status set.

        Args:
            path: Repository-relative file path to check.
            set_name: Name of the set to check: "staged", "modified",
                     "untracked", or "conflict".

        Returns:
            True if file is in the specified set, False otherwise.
        """
        if self.git is None:
            return False
        if not isinstance(path, str) or not isinstance(set_name, str):
            return False

        sets: dict[str, frozenset[str]] = {
            "staged": self.git.staged_files,
            "modified": self.git.modified_files,
            "untracked": self.git.untracked_files,
            "conflict": self.git.conflict_files,
        }

        file_set = sets.get(set_name)
        if file_set is None:
            return False
        return path in file_set
