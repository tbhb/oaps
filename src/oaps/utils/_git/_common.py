"""Common git utility functions.

This module provides shared helper functions used by git-related utilities
including repository discovery, path handling, and byte/string conversion.
"""

from pathlib import Path

from dulwich.errors import NotGitRepository
from dulwich.repo import Repo

from oaps.exceptions import OAPSError


def decode_bytes(value: bytes | str) -> str:
    """Decode bytes to str if needed.

    Args:
        value: A bytes or str value.

    Returns:
        The value as a string.
    """
    if isinstance(value, bytes):
        return value.decode()
    return value


def discover_repo(cwd: Path | str | None = None) -> Repo | None:
    """Discover git repository from the given directory.

    Args:
        cwd: Directory to start search from. If None, uses current directory.

    Returns:
        Repo instance if found, None otherwise.
    """
    try:
        if cwd is not None:
            return Repo.discover(str(cwd))
        return Repo.discover()
    except NotGitRepository:
        return None


def resolve_repo(repo_path: Path | None = None) -> Repo:
    """Resolve a repository from the given path or discover it.

    Args:
        repo_path: Optional path to the repository. If None, uses Repo.discover().

    Returns:
        The resolved Repo instance.

    Raises:
        OAPSError: If no Git repository is found.
    """
    try:
        if repo_path is not None:
            return Repo(str(repo_path))
        return Repo.discover()
    except NotGitRepository as e:
        msg = "Not inside a Git repository"
        raise OAPSError(msg) from e


def get_worktree_dir(repo: Repo) -> Path:
    """Get the worktree directory for a repository.

    Args:
        repo: The repository instance.

    Returns:
        Path to the worktree directory.
    """
    repo_path = repo.path
    if isinstance(repo_path, bytes):
        repo_path = repo_path.decode()

    path = Path(repo_path)
    # If path is .git directory, return parent
    if path.name == ".git":
        return path.parent
    return path


def get_main_worktree_dir(repo: Repo) -> Path:
    """Get the main worktree directory for a repository.

    Args:
        repo: The repository instance.

    Returns:
        Path to the main worktree directory.
    """
    commondir = repo.commondir()
    if isinstance(commondir, bytes):
        commondir = commondir.decode()

    path = Path(commondir).resolve()
    # commondir points to .git directory, return parent
    if path.name == ".git":
        return path.parent
    return path


def get_main_repo(repo: Repo) -> Repo:
    """Get the main repository from any repo (including linked worktrees).

    When Repo.discover() is called from a linked worktree, it returns a Repo
    scoped to that worktree. This function returns the main repository that
    contains all worktree information.

    Args:
        repo: Any repository instance (main or linked worktree).

    Returns:
        The main repository instance.
    """
    # Get the commondir which points to the main .git directory
    commondir = repo.commondir()
    # Handle both bytes and str from commondir (dulwich internals may return bytes)
    if isinstance(commondir, bytes):
        commondir = commondir.decode()
    main_git_dir = Path(commondir).resolve()

    # If it's already the main repo, return as-is
    repo_path = Path(repo.path.decode() if isinstance(repo.path, bytes) else repo.path)
    if repo_path.resolve() == main_git_dir:
        return repo

    # Otherwise, create a new Repo from the main .git directory
    return Repo(str(main_git_dir))


def strip_refs_heads(branch: bytes | str | None) -> str | None:
    """Strip refs/heads/ prefix from a branch reference.

    Args:
        branch: Branch reference (bytes or str), possibly with refs/heads/ prefix.

    Returns:
        Branch name without prefix, or None if input is None.
    """
    if branch is None:
        return None
    branch_str = branch.decode() if isinstance(branch, bytes) else branch
    if branch_str.startswith("refs/heads/"):
        return branch_str[11:]
    return branch_str
