"""Git context dataclass.

This module provides the GitContext dataclass which contains information
about a Git repository's current state including branch, commit, and file status.
"""

# ruff: noqa: TC003  # Path needed at runtime for dataclass field
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class GitContext:
    """Context information for Git operations.

    All file paths in the file sets are repository-relative strings,
    not absolute paths.

    Attributes:
        main_worktree_dir: Path to the main worktree directory.
        worktree_dir: Path to the current worktree directory.
        head_commit: Current HEAD commit SHA as hex string, or None if no commits.
        is_detached: Whether HEAD is detached.
        is_dirty: Whether the repository has uncommitted changes.
        conflict_files: Frozenset of repository-relative paths with merge conflicts.
        staged_files: Frozenset of repository-relative paths that are staged.
        modified_files: Frozenset of repository-relative paths that are modified
            but unstaged.
        untracked_files: Frozenset of repository-relative paths that are untracked.
        branch: Current branch name (without refs/heads/ prefix), or None if
            detached.
        tag: Tag name pointing to HEAD (without refs/tags/ prefix), or None.
    """

    main_worktree_dir: Path
    worktree_dir: Path

    head_commit: str | None
    is_detached: bool
    is_dirty: bool

    conflict_files: frozenset[str] = field(default_factory=frozenset)
    staged_files: frozenset[str] = field(default_factory=frozenset)
    modified_files: frozenset[str] = field(default_factory=frozenset)
    untracked_files: frozenset[str] = field(default_factory=frozenset)

    branch: str | None = None
    tag: str | None = None
