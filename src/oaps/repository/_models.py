# ruff: noqa: TC003  # Path and datetime needed at runtime for dataclass fields
"""OAPS repository models.

This module defines data structures for representing OAPS repository state.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OapsRepoStatus:
    """File status snapshot for the OAPS repository.

    Attributes:
        staged: Files that are staged for commit.
        modified: Files that are modified but not staged.
        untracked: Files that are not tracked by git.
    """

    staged: frozenset[Path]
    modified: frozenset[Path]
    untracked: frozenset[Path]


@dataclass(frozen=True, slots=True)
class ProjectRepoStatus:
    """File status snapshot for the project repository.

    Attributes:
        staged: Files that are staged for commit.
        modified: Files that are modified but not staged.
        untracked: Files that are not tracked by git.
    """

    staged: frozenset[Path]
    modified: frozenset[Path]
    untracked: frozenset[Path]


# Type alias for union of all status types
type RepoStatus = OapsRepoStatus | ProjectRepoStatus


@dataclass(frozen=True, slots=True)
class CommitResult:
    """Result of a commit operation.

    Attributes:
        sha: Commit SHA hex string, None if no_changes.
        files: Files included in commit (absolute paths).
        no_changes: True if nothing was committed.
    """

    sha: str | None
    files: frozenset[Path]
    no_changes: bool


@dataclass(frozen=True, slots=True)
class CommitInfo:
    """Information about a single commit.

    Attributes:
        sha: Full 40-character commit SHA hex string.
        message: Complete commit message (subject + body).
        author_name: Author name from commit.
        author_email: Author email from commit.
        timestamp: Commit timestamp as UTC datetime.
        files_changed: Number of files changed in this commit.
        parent_shas: SHA hex strings of parent commits (empty tuple for initial commit).
    """

    sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: datetime
    files_changed: int
    parent_shas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DiscardResult:
    """Result of a discard_changes operation.

    Attributes:
        unstaged: Files that were unstaged from the index.
        restored: Files restored to HEAD state in working tree.
        no_changes: True if nothing was discarded.
    """

    unstaged: frozenset[Path]
    restored: frozenset[Path]
    no_changes: bool


@dataclass(frozen=True, slots=True)
class FileDiffStats:
    """Diff statistics for a single file.

    Attributes:
        path: Repository-relative path to the file.
        additions: Number of lines added.
        deletions: Number of lines deleted.
        is_binary: True if file is binary (additions/deletions will be 0).
        is_new: True if file is newly added.
        is_deleted: True if file was deleted.
        is_renamed: True if file was renamed.
        old_path: Previous path if renamed, None otherwise.
    """

    path: str
    additions: int
    deletions: int
    is_binary: bool = False
    is_new: bool = False
    is_deleted: bool = False
    is_renamed: bool = False
    old_path: str | None = None


@dataclass(frozen=True, slots=True)
class DiffStats:
    """Aggregate diff statistics.

    Attributes:
        files: Per-file statistics (tuple preserves order).
        total_additions: Sum of all additions.
        total_deletions: Sum of all deletions.
        files_changed: Number of files changed.
    """

    files: tuple[FileDiffStats, ...]
    total_additions: int
    total_deletions: int
    files_changed: int


@dataclass(frozen=True, slots=True)
class BlameLine:
    """Information about a single blamed line.

    Represents the authorship and content of one line in a file,
    as returned by git blame.

    Attributes:
        line_no: 1-based line number in the file.
        content: The actual line content (without trailing newline).
        sha: The commit SHA that last modified this line (40-char hex).
        author_name: Name of the author who last modified this line.
        author_email: Email of the author who last modified this line.
        timestamp: When the line was last modified (UTC datetime with timezone).
    """

    line_no: int
    content: str
    sha: str
    author_name: str
    author_email: str
    timestamp: datetime
