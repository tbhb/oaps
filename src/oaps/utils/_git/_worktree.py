"""Git worktree utility functions.

This module provides functions for managing Git worktrees using dulwich.
It follows Clean Architecture principles with clear separation between
query and mutation operations.
"""

from dataclasses import dataclass
from pathlib import Path

from dulwich.errors import NotGitRepository
from dulwich.repo import Repo
from dulwich.worktree import WorkTreeContainer, WorkTreeInfo as DulwichWorkTreeInfo

from oaps.exceptions import (
    WorktreeDirtyError,
    WorktreeError,
    WorktreeLockedError,
    WorktreeNotFoundError,
)
from oaps.repository import OapsRepository, ProjectRepository
from oaps.utils._git._common import get_main_repo, resolve_repo, strip_refs_heads


@dataclass(frozen=True, slots=True)
class WorktreeInfo:
    """Information about a Git worktree.

    Attributes:
        path: Path to the worktree directory.
        head_commit: Current HEAD commit SHA as hex string, or None if bare.
        branch: Current branch name (without refs/heads/ prefix), or None.
        is_main: Whether this is the main worktree.
        is_bare: Whether this is a bare repository.
        is_detached: Whether HEAD is detached.
        is_locked: Whether the worktree is locked.
        is_prunable: Whether the worktree can be pruned.
        lock_reason: Reason for locking, if locked.
    """

    path: Path
    head_commit: str | None
    branch: str | None
    is_main: bool
    is_bare: bool
    is_detached: bool
    is_locked: bool
    is_prunable: bool
    lock_reason: str | None


@dataclass(frozen=True, slots=True)
class WorktreeAddResult:
    """Result of adding a worktree.

    Attributes:
        worktree: Information about the created worktree.
        created_branch: Name of the branch that was created, or None if existing.
    """

    worktree: WorktreeInfo
    created_branch: str | None


@dataclass(frozen=True, slots=True)
class WorktreePruneResult:
    """Result of pruning worktrees.

    Attributes:
        pruned_ids: Tuple of pruned worktree identifiers.
        dry_run: Whether this was a dry run (no actual pruning).
    """

    pruned_ids: tuple[str, ...]
    dry_run: bool


def _find_worktree_by_path(
    container: WorkTreeContainer, path: Path
) -> DulwichWorkTreeInfo:
    """Find a worktree by its path.

    Args:
        container: The worktree container to search.
        path: Path to the worktree.

    Returns:
        The dulwich WorkTreeInfo for the worktree.

    Raises:
        WorktreeNotFoundError: If no worktree exists at the path.
    """
    resolved_path = path.resolve()
    for wt in container.list():
        if Path(wt.path).resolve() == resolved_path:
            return wt
    msg = f"No worktree found at {path}"
    raise WorktreeNotFoundError(msg)


def _convert_worktree_info(
    dulwich_info: DulwichWorkTreeInfo, *, is_main: bool = False
) -> WorktreeInfo:
    """Convert dulwich WorkTreeInfo to OAPS WorktreeInfo.

    Args:
        dulwich_info: Dulwich worktree information object.
        is_main: Whether this is the main worktree.

    Returns:
        OAPS WorktreeInfo instance.
    """
    head_commit: str | None = None
    if dulwich_info.head is not None:
        head_commit = dulwich_info.head.decode()

    # The main worktree path might be .git directory, normalize to parent
    worktree_path = Path(dulwich_info.path)
    if worktree_path.name == ".git":
        worktree_path = worktree_path.parent

    return WorktreeInfo(
        path=worktree_path,
        head_commit=head_commit,
        branch=strip_refs_heads(dulwich_info.branch),
        is_main=is_main,
        is_bare=dulwich_info.bare,
        is_detached=dulwich_info.detached,
        is_locked=dulwich_info.locked,
        is_prunable=dulwich_info.prunable,
        lock_reason=dulwich_info.lock_reason,
    )


# Query Functions
# ===============


def list_worktrees(repo_path: Path | None = None) -> list[WorktreeInfo]:
    """List all worktrees for a repository.

    Args:
        repo_path: Optional path to the repository. If None, auto-discovers.

    Returns:
        List of WorktreeInfo objects for all worktrees.

    Raises:
        OAPSError: If no Git repository is found.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)
    worktrees = container.list()

    result: list[WorktreeInfo] = []
    for i, wt in enumerate(worktrees):
        # The first worktree in the list is the main worktree
        result.append(_convert_worktree_info(wt, is_main=(i == 0)))

    return result


def get_worktree(path: Path | None = None) -> WorktreeInfo | None:
    """Get worktree information for a specific path.

    Args:
        path: Path to check. If None, uses current working directory.

    Returns:
        WorktreeInfo if the path is a worktree, None otherwise.
    """
    check_path = path if path is not None else Path.cwd()

    try:
        repo = Repo.discover(str(check_path))
    except NotGitRepository:
        return None

    container = WorkTreeContainer(repo)
    worktrees = container.list()

    for i, wt in enumerate(worktrees):
        wt_path = Path(wt.path).resolve()
        if wt_path == check_path.resolve():
            return _convert_worktree_info(wt, is_main=(i == 0))

    return None


def get_main_worktree(repo_path: Path | None = None) -> WorktreeInfo:
    """Get the main worktree for a repository.

    Args:
        repo_path: Optional path to the repository. If None, auto-discovers.

    Returns:
        WorktreeInfo for the main worktree.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeError: If no worktrees exist (corrupted repository).
    """
    worktrees = list_worktrees(repo_path)
    if not worktrees:
        msg = "No worktrees found in repository"
        raise WorktreeError(msg)
    # The first worktree is always the main worktree
    return worktrees[0]


def get_worktree_for_path(path: Path) -> WorktreeInfo | None:
    """Get the worktree that contains a given path.

    This differs from get_worktree() in that it finds the worktree
    containing any path, not just the worktree root itself.

    Args:
        path: Path to find the containing worktree for.

    Returns:
        WorktreeInfo if the path is within a worktree, None otherwise.
    """
    try:
        repo = Repo.discover(str(path))
    except NotGitRepository:
        return None

    # Get the main repo to properly list all worktrees
    main_repo = get_main_repo(repo)
    container = WorkTreeContainer(main_repo)
    worktrees = container.list()

    resolved_path = path.resolve()

    for i, wt in enumerate(worktrees):
        wt_path = Path(wt.path).resolve()
        # Normalize .git path to parent directory
        if wt_path.name == ".git":
            wt_path = wt_path.parent
        try:
            _ = resolved_path.relative_to(wt_path)
            return _convert_worktree_info(wt, is_main=(i == 0))
        except ValueError:
            continue

    return None


def is_in_worktree(path: Path | None = None) -> bool:
    """Check if a path is within a Git worktree.

    Args:
        path: Path to check. If None, uses current working directory.

    Returns:
        True if the path is within a worktree, False otherwise.
    """
    check_path = path if path is not None else Path.cwd()
    return get_worktree_for_path(check_path) is not None


def is_main_worktree(path: Path | None = None) -> bool:
    """Check if a path is within the main worktree.

    Args:
        path: Path to check. If None, uses current working directory.

    Returns:
        True if the path is within the main worktree, False otherwise.
    """
    check_path = path if path is not None else Path.cwd()
    worktree = get_worktree_for_path(check_path)
    return worktree is not None and worktree.is_main


def get_project_repository_for_worktree(
    worktree_path: Path | None = None,
) -> ProjectRepository:
    """Get a ProjectRepository for a specific worktree.

    This factory function resolves the worktree containing the given path
    and returns a ProjectRepository scoped to that worktree. This is useful
    when working with multiple worktrees and needing to access the project
    repository for a specific one.

    Args:
        worktree_path: Path within a worktree. If None, uses current working
            directory.

    Returns:
        ProjectRepository for the resolved worktree.

    Raises:
        WorktreeNotFoundError: If no worktree contains the given path.
        ProjectRepositoryNotInitializedError: If .git not found.

    Example:
        >>> repo = get_project_repository_for_worktree(Path("/path/to/worktree"))
        >>> with repo:
        ...     status = repo.get_status()
    """
    check_path = worktree_path if worktree_path is not None else Path.cwd()
    worktree = get_worktree_for_path(check_path)
    if worktree is None:
        msg = f"No worktree found at {check_path}"
        raise WorktreeNotFoundError(msg)
    return ProjectRepository(worktree_dir=worktree.path)


def get_oaps_repository_for_worktree(
    worktree_path: Path | None = None,
) -> OapsRepository:
    """Get an OapsRepository for a specific worktree.

    This factory function resolves the worktree containing the given path
    and returns an OapsRepository for the .oaps/ directory within that worktree.
    Symlinked .oaps/ directories are resolved to find the actual location.

    Args:
        worktree_path: Path within a worktree. If None, uses current working
            directory.

    Returns:
        OapsRepository for the resolved .oaps/ directory.

    Raises:
        WorktreeNotFoundError: If no worktree contains the given path.
        OapsRepositoryNotInitializedError: If .oaps/.git not found.

    Example:
        >>> repo = get_oaps_repository_for_worktree(Path("/path/to/worktree"))
        >>> with repo:
        ...     status = repo.get_status()
    """
    check_path = worktree_path if worktree_path is not None else Path.cwd()
    worktree = get_worktree_for_path(check_path)
    if worktree is None:
        msg = f"No worktree found at {check_path}"
        raise WorktreeNotFoundError(msg)

    # Resolve symlink to find actual .oaps/ location
    oaps_path = (worktree.path / ".oaps").resolve()
    # OapsRepository expects working_dir to contain .oaps/
    return OapsRepository(working_dir=oaps_path.parent)


# Mutation Functions
# ==================


def add_worktree(  # noqa: PLR0913
    path: Path,
    branch: str | None = None,
    commit: str | None = None,
    *,
    force: bool = False,
    detach: bool = False,
    repo_path: Path | None = None,
) -> WorktreeAddResult:
    """Add a new worktree.

    Args:
        path: Path where the new worktree should be created.
        branch: Branch to checkout in the new worktree.
        commit: Specific commit to checkout (results in detached HEAD).
        force: Force creation even if branch is already checked out elsewhere.
        detach: Detach HEAD in the new worktree.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Returns:
        WorktreeAddResult with information about the created worktree.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeError: If the worktree cannot be created.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    # Determine if we're creating a new branch
    created_branch: str | None = None
    branch_bytes: bytes | None = None
    if branch is not None:
        branch_bytes = branch.encode()
        # Check if branch exists
        refs = repo.refs
        branch_ref = f"refs/heads/{branch}".encode()
        if branch_ref not in refs:
            created_branch = branch

    commit_bytes: bytes | None = None
    if commit is not None:
        commit_bytes = commit.encode()

    try:
        _ = container.add(
            path=str(path),
            branch=branch_bytes,
            commit=commit_bytes,
            force=force,
            detach=detach,
        )
    except Exception as e:
        msg = f"Failed to add worktree at {path}: {e}"
        raise WorktreeError(msg) from e

    # Get the newly created worktree info
    worktrees = container.list()
    resolved_path = path.resolve()

    for wt in worktrees:
        if Path(wt.path).resolve() == resolved_path:
            return WorktreeAddResult(
                worktree=_convert_worktree_info(wt, is_main=False),
                created_branch=created_branch,
            )

    # Should not reach here, but handle gracefully
    msg = f"Worktree was added but not found at {path}"
    raise WorktreeError(msg)


def remove_worktree(
    path: Path,
    *,
    force: bool = False,
    repo_path: Path | None = None,
) -> None:
    """Remove a worktree.

    Args:
        path: Path to the worktree to remove.
        force: Force removal even if there are local changes.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeNotFoundError: If no worktree exists at the path.
        WorktreeLockedError: If the worktree is locked.
        WorktreeDirtyError: If there are uncommitted changes and force is False.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    # Find the worktree and check lock status
    wt = _find_worktree_by_path(container, path)

    if wt.locked and not force:
        reason_msg = f": {wt.lock_reason}" if wt.lock_reason else ""
        msg = f"Worktree at {path} is locked{reason_msg}"
        raise WorktreeLockedError(msg)

    try:
        container.remove(str(path), force=force)
    except Exception as e:
        error_str = str(e).lower()
        if "uncommitted" in error_str or "dirty" in error_str or "changes" in error_str:
            msg = f"Worktree at {path} has uncommitted changes"
            raise WorktreeDirtyError(msg) from e
        msg = f"Failed to remove worktree at {path}: {e}"
        raise WorktreeError(msg) from e


def move_worktree(
    old_path: Path,
    new_path: Path,
    *,
    repo_path: Path | None = None,
) -> WorktreeInfo:
    """Move a worktree to a new location.

    Args:
        old_path: Current path of the worktree.
        new_path: New path for the worktree.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Returns:
        WorktreeInfo for the moved worktree.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeNotFoundError: If no worktree exists at old_path.
        WorktreeLockedError: If the worktree is locked.
        WorktreeError: If the move fails.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    # Find the worktree and check lock status
    wt = _find_worktree_by_path(container, old_path)

    if wt.locked:
        reason_msg = f": {wt.lock_reason}" if wt.lock_reason else ""
        msg = f"Worktree at {old_path} is locked{reason_msg}"
        raise WorktreeLockedError(msg)

    try:
        container.move(str(old_path), str(new_path))
    except Exception as e:
        msg = f"Failed to move worktree from {old_path} to {new_path}: {e}"
        raise WorktreeError(msg) from e

    # Get the moved worktree info
    moved_wt = _find_worktree_by_path(container, new_path)
    return _convert_worktree_info(moved_wt, is_main=False)


def lock_worktree(
    path: Path,
    reason: str | None = None,
    *,
    repo_path: Path | None = None,
) -> None:
    """Lock a worktree to prevent it from being pruned.

    Args:
        path: Path to the worktree to lock.
        reason: Optional reason for locking.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeNotFoundError: If no worktree exists at the path.
        WorktreeError: If locking fails.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    # Verify the worktree exists
    _ = _find_worktree_by_path(container, path)

    try:
        container.lock(str(path), reason=reason)
    except Exception as e:
        msg = f"Failed to lock worktree at {path}: {e}"
        raise WorktreeError(msg) from e


def unlock_worktree(
    path: Path,
    *,
    repo_path: Path | None = None,
) -> None:
    """Unlock a worktree.

    Args:
        path: Path to the worktree to unlock.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeNotFoundError: If no worktree exists at the path.
        WorktreeError: If unlocking fails.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    # Verify the worktree exists
    _ = _find_worktree_by_path(container, path)

    try:
        container.unlock(str(path))
    except Exception as e:
        msg = f"Failed to unlock worktree at {path}: {e}"
        raise WorktreeError(msg) from e


def prune_worktrees(
    *,
    dry_run: bool = False,
    repo_path: Path | None = None,
) -> WorktreePruneResult:
    """Prune worktree administrative files for missing worktrees.

    Args:
        dry_run: Don't actually remove anything, just report what would be removed.
        repo_path: Optional path to the repository. If None, auto-discovers.

    Returns:
        WorktreePruneResult with list of pruned worktree identifiers.

    Raises:
        OAPSError: If no Git repository is found.
        WorktreeError: If pruning fails.
    """
    repo = resolve_repo(repo_path)
    container = WorkTreeContainer(repo)

    try:
        pruned = container.prune(dry_run=dry_run)
    except Exception as e:
        msg = f"Failed to prune worktrees: {e}"
        raise WorktreeError(msg) from e

    return WorktreePruneResult(
        pruned_ids=tuple(pruned),
        dry_run=dry_run,
    )
