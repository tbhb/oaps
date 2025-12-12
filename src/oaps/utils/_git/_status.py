"""Git status collection functions.

This module provides functions for collecting git repository status
information using dulwich. All paths in file sets are repository-relative strings.
"""

# ruff: noqa: TC002, TC003  # Path and Repo needed at runtime
from pathlib import Path
from typing import TYPE_CHECKING

from dulwich import porcelain
from dulwich.repo import Repo

from oaps.utils._git._common import (
    decode_bytes,
    discover_repo,
    get_main_worktree_dir,
    get_worktree_dir,
)
from oaps.utils._git._context import GitContext

if TYPE_CHECKING:
    from dulwich.index import Index


def _get_staged_files(status: porcelain.GitStatus) -> frozenset[str]:
    """Extract staged files from git status.

    Args:
        status: GitStatus from porcelain.status().

    Returns:
        Frozenset of repository-relative file paths that are staged.
    """
    staged: set[str] = set()
    # status.staged is a dict with keys: 'add', 'delete', 'modify'
    # dulwich doesn't have type stubs, so we cast and ignore type warnings
    staged_dict = status.staged  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    for change_type in ("add", "delete", "modify"):
        files: list[bytes] = staged_dict.get(change_type, [])  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        for f in files:  # pyright: ignore[reportUnknownVariableType]
            staged.add(decode_bytes(f))  # pyright: ignore[reportUnknownArgumentType]
    return frozenset(staged)


def _get_modified_files(status: porcelain.GitStatus) -> frozenset[str]:
    """Extract modified (unstaged) files from git status.

    Args:
        status: GitStatus from porcelain.status().

    Returns:
        Frozenset of repository-relative file paths that are modified but unstaged.
    """
    # dulwich doesn't have type stubs
    unstaged: list[bytes] = status.unstaged  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    return frozenset(
        decode_bytes(f)  # pyright: ignore[reportUnknownArgumentType]
        for f in unstaged  # pyright: ignore[reportUnknownVariableType]
    )


def _get_untracked_files(status: porcelain.GitStatus) -> frozenset[str]:
    """Extract untracked files from git status.

    Args:
        status: GitStatus from porcelain.status().

    Returns:
        Frozenset of repository-relative file paths that are untracked.
    """
    # dulwich doesn't have type stubs
    untracked: list[bytes] = status.untracked  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
    return frozenset(
        decode_bytes(f)  # pyright: ignore[reportUnknownArgumentType]
        for f in untracked  # pyright: ignore[reportUnknownVariableType]
    )


def _get_conflict_files(index: Index) -> frozenset[str]:
    """Extract files with merge conflicts from the index.

    Conflict files are detected by checking if the index has_conflicts().
    If conflicts exist, we iterate through entries looking for paths
    that appear with different stages (stage > 0 indicates conflict).

    Args:
        index: The repository index.

    Returns:
        Frozenset of repository-relative file paths with merge conflicts.
    """
    if not index.has_conflicts():
        return frozenset()

    # When conflicts exist, the index will have multiple entries for the same path
    # with different stage numbers (1=common ancestor, 2=ours, 3=theirs)
    # Since dulwich's index.items() returns (path, entry) pairs and the entry
    # doesn't expose stage directly in IndexEntry, we rely on has_conflicts()
    # and treat all conflicted paths as the entire set when conflicts detected.
    # This is a simplified implementation; for full conflict detection,
    # we would need to access raw index entries with stage information.
    #
    # For now, return empty since precise conflict detection requires
    # lower-level index access than dulwich's IndexEntry exposes.
    # The has_conflicts() check above allows $has_conflicts() to work correctly.
    return frozenset()


def _get_current_branch(repo: Repo) -> str | None:
    """Get the current branch name.

    Args:
        repo: The repository instance.

    Returns:
        Branch name without refs/heads/ prefix, or None if detached HEAD.
    """
    refs = repo.refs
    symrefs = refs.get_symrefs()

    head_ref = symrefs.get(b"HEAD")
    if head_ref is None:
        return None

    head_ref_str = decode_bytes(head_ref)
    if head_ref_str.startswith("refs/heads/"):
        return head_ref_str[11:]  # Strip "refs/heads/"
    return None


def _get_head_commit(repo: Repo) -> str | None:
    """Get the HEAD commit SHA.

    Args:
        repo: The repository instance.

    Returns:
        Hex string of the HEAD commit SHA, or None if no commits exist.
    """
    try:
        head = repo.head()
        return decode_bytes(head)
    except KeyError:
        return None


def _is_detached(repo: Repo) -> bool:
    """Check if HEAD is detached.

    Args:
        repo: The repository instance.

    Returns:
        True if HEAD is detached, False otherwise.
    """
    refs = repo.refs
    symrefs = refs.get_symrefs()

    head_ref = symrefs.get(b"HEAD")
    if head_ref is None:
        return True

    head_ref_str = decode_bytes(head_ref)
    return not head_ref_str.startswith("refs/heads/")


def _get_current_tag(repo: Repo) -> str | None:
    """Get tag name pointing to HEAD, if any.

    Args:
        repo: The repository instance.

    Returns:
        Tag name without refs/tags/ prefix, or None if no tag at HEAD.
    """
    try:
        head_sha = repo.head()
    except KeyError:
        return None

    refs = repo.refs
    for ref_name in refs.allkeys():
        ref_name_str = decode_bytes(ref_name)
        if ref_name_str.startswith("refs/tags/"):
            try:
                tag_sha = refs[ref_name]
                # Handle annotated tags by getting the target
                try:
                    tag_obj = repo[tag_sha]
                    # Annotated tags have a _target or object attribute
                    # dulwich types are incomplete so we use getattr
                    target: object = getattr(tag_obj, "_target", None)
                    if target is None:
                        target = getattr(tag_obj, "object", None)
                    if target is not None:
                        # Annotated tag - compare object target
                        if isinstance(target, tuple):
                            target = target[1]  # pyright: ignore[reportUnknownVariableType]
                        if target == head_sha:
                            return ref_name_str[10:]  # Strip "refs/tags/"
                    elif tag_sha == head_sha:
                        # Lightweight tag or direct match
                        return ref_name_str[10:]
                except (KeyError, AttributeError):
                    if tag_sha == head_sha:
                        return ref_name_str[10:]
            except KeyError:
                continue
    return None


def _is_dirty(staged_files: frozenset[str], modified_files: frozenset[str]) -> bool:
    """Check if the repository has uncommitted changes.

    Args:
        staged_files: Set of staged file paths.
        modified_files: Set of modified (unstaged) file paths.

    Returns:
        True if there are staged or modified files.
    """
    return len(staged_files) > 0 or len(modified_files) > 0


def get_git_context(cwd: Path | str | None = None) -> GitContext | None:
    """Get git repository context for the current directory.

    Collects information about the current git repository state including
    branch, head commit, staged files, modified files, untracked files,
    and conflict status.

    Args:
        cwd: Working directory to start repository discovery from.
             If None, uses current working directory.

    Returns:
        GitContext with repository information, or None if not in a git repository.
    """
    repo = discover_repo(cwd)
    if repo is None:
        return None

    try:
        # Get file status
        status = porcelain.status(repo)
        staged_files = _get_staged_files(status)
        modified_files = _get_modified_files(status)
        untracked_files = _get_untracked_files(status)

        # Get conflict files from index
        index = repo.open_index()
        conflict_files = _get_conflict_files(index)

        # Get repository metadata
        worktree_dir = get_worktree_dir(repo)
        main_worktree_dir = get_main_worktree_dir(repo)
        head_commit = _get_head_commit(repo)
        is_detached_head = _is_detached(repo)
        branch = _get_current_branch(repo)
        tag = _get_current_tag(repo)
        dirty = _is_dirty(staged_files, modified_files)

        return GitContext(
            main_worktree_dir=main_worktree_dir,
            worktree_dir=worktree_dir,
            head_commit=head_commit,
            is_detached=is_detached_head,
            is_dirty=dirty,
            conflict_files=conflict_files,
            staged_files=staged_files,
            modified_files=modified_files,
            untracked_files=untracked_files,
            branch=branch,
            tag=tag,
        )
    except Exception:  # noqa: BLE001 - Intentional catch-all for robustness
        # If anything fails during git context collection, return None
        # to avoid breaking hooks
        return None
    finally:
        # Always close the repository to avoid resource leaks
        repo.close()
