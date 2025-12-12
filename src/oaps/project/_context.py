"""Project repository context for hooks and expressions.

This module provides dataclasses and functions for extracting project
repository context information, excluding the .oaps/ directory.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from oaps.exceptions import ProjectRepositoryNotInitializedError
from oaps.repository import ProjectRepository

if TYPE_CHECKING:
    from oaps.repository._models import CommitInfo, DiffStats


@dataclass(frozen=True, slots=True)
class ProjectDiffStats:
    """Simplified diff statistics for project context.

    Attributes:
        total_additions: Total number of lines added across all files.
        total_deletions: Total number of lines deleted across all files.
        files_changed: Number of files with changes.
    """

    total_additions: int
    total_deletions: int
    files_changed: int


@dataclass(frozen=True, slots=True)
class ProjectCommitInfo:
    """Commit information for project context.

    Note: timestamp is ISO 8601 string for JSON serialization.

    Attributes:
        sha: Full 40-character commit SHA hex string.
        message: Complete commit message (subject + body).
        author_name: Author name from commit.
        author_email: Author email from commit.
        timestamp: Commit timestamp as ISO 8601 string.
        files_changed: Number of files changed in this commit.
        parent_shas: SHA hex strings of parent commits.
    """

    sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: str  # ISO 8601 format
    files_changed: int
    parent_shas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectContext:
    """Project repository context for hooks and expressions.

    Provides a snapshot of the project's git repository state,
    excluding the .oaps/ directory. All fields are JSON-serializable.

    Attributes:
        has_changes: True if there are any uncommitted changes.
        uncommitted_count: Total count of uncommitted files (staged + modified).
        staged_count: Number of files staged for commit.
        modified_count: Number of files modified but not staged.
        untracked_count: Number of untracked files.
        diff_stats: Diff statistics if requested, None otherwise.
        recent_commits: Tuple of recent commits.
    """

    has_changes: bool
    uncommitted_count: int
    staged_count: int
    modified_count: int
    untracked_count: int
    diff_stats: ProjectDiffStats | None
    recent_commits: tuple[ProjectCommitInfo, ...]


def _combine_diff_stats(staged: DiffStats, unstaged: DiffStats) -> ProjectDiffStats:
    """Combine staged and unstaged DiffStats into ProjectDiffStats.

    Args:
        staged: DiffStats for staged changes.
        unstaged: DiffStats for unstaged changes.

    Returns:
        ProjectDiffStats with combined statistics.
    """
    return ProjectDiffStats(
        total_additions=staged.total_additions + unstaged.total_additions,
        total_deletions=staged.total_deletions + unstaged.total_deletions,
        files_changed=staged.files_changed + unstaged.files_changed,
    )


def _convert_commit_info(commit: CommitInfo) -> ProjectCommitInfo:
    """Convert repository CommitInfo to ProjectCommitInfo.

    Args:
        commit: CommitInfo from ProjectRepository.

    Returns:
        ProjectCommitInfo with timestamp as ISO 8601 string.
    """
    return ProjectCommitInfo(
        sha=commit.sha,
        message=commit.message,
        author_name=commit.author_name,
        author_email=commit.author_email,
        timestamp=commit.timestamp.isoformat(),
        files_changed=commit.files_changed,
        parent_shas=commit.parent_shas,
    )


def get_project_context(
    cwd: Path | str | None = None,
    *,
    include_diff_stats: bool = False,
    recent_commits_count: int = 5,
) -> ProjectContext | None:
    """Get project repository context.

    Collects information about the project git repository state,
    excluding the .oaps/ directory. This is useful for hook conditions
    that need to check project state.

    Args:
        cwd: Working directory for repository discovery. If None, uses cwd.
        include_diff_stats: Whether to include diff statistics (slower).
        recent_commits_count: Number of recent commits to include.

    Returns:
        ProjectContext or None if not in a git repository.
    """
    # Resolve cwd
    if cwd is None:
        resolved_cwd = Path.cwd()
    elif isinstance(cwd, str):
        resolved_cwd = Path(cwd)
    else:
        resolved_cwd = cwd

    try:
        with ProjectRepository(worktree_dir=resolved_cwd) as repo:
            # Get status
            status = repo.get_status()

            # Calculate counts
            staged_count = len(status.staged)
            modified_count = len(status.modified)
            untracked_count = len(status.untracked)
            uncommitted_count = staged_count + modified_count
            has_changes = uncommitted_count > 0

            # Get diff stats if requested
            diff_stats: ProjectDiffStats | None = None
            if include_diff_stats and has_changes:
                # Get both staged and unstaged diff stats and combine
                staged_stats = repo.get_diff_stats(staged=True)
                unstaged_stats = repo.get_diff_stats(staged=False)
                diff_stats = _combine_diff_stats(staged_stats, unstaged_stats)

            # Get recent commits
            commits = repo.get_log(n=recent_commits_count)
            recent_commits = tuple(_convert_commit_info(c) for c in commits)

            return ProjectContext(
                has_changes=has_changes,
                uncommitted_count=uncommitted_count,
                staged_count=staged_count,
                modified_count=modified_count,
                untracked_count=untracked_count,
                diff_stats=diff_stats,
                recent_commits=recent_commits,
            )
    except ProjectRepositoryNotInitializedError:
        return None
    except Exception:  # noqa: BLE001 - Intentional catch-all for robustness
        # If anything fails during context collection, return None
        # to avoid breaking hooks
        return None
