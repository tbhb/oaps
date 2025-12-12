# ruff: noqa: TC003  # Path needed at runtime for Protocol method bodies
"""Repository protocol for type-safe dependency injection.

This module defines a runtime-checkable Protocol that both OapsRepository
and ProjectRepository satisfy, enabling type-safe dependency injection
and testing with fakes.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from oaps.repository._models import CommitInfo, CommitResult, DiscardResult


@runtime_checkable
class RepositoryProtocol(Protocol):
    """Protocol for scoped Git repository operations.

    Both OapsRepository and ProjectRepository implement this protocol,
    enabling type-safe dependency injection and testing with fakes.

    This protocol defines the minimal interface needed for consumers
    that need to interact with a Git repository without knowing which
    specific repository type they're working with.

    Example:
        >>> def save_changes(repo: RepositoryProtocol, message: str) -> None:
        ...     if repo.has_changes():
        ...         repo.commit(message)
        >>> # Works with either repository type
        >>> with OapsRepository() as oaps_repo:
        ...     save_changes(oaps_repo, "Update config")
    """

    @property
    def root(self) -> Path:
        """Root directory for this repository's scope.

        Returns:
            The absolute path to the repository root directory.
        """
        ...

    def close(self) -> None:
        """Close the underlying git repository.

        Releases file handles held by the repository. This method is
        automatically called when using the context manager protocol.
        """
        ...

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes in scope.

        Returns:
            True if there are staged, modified, or untracked files.
        """
        ...

    def get_uncommitted_files(self) -> set[Path]:
        """Get all files with uncommitted changes.

        Returns:
            Set of absolute paths to files that are staged, modified,
            or untracked.
        """
        ...

    def validate_path(self, path: Path) -> bool:
        """Check if path is within this repository's scope.

        Args:
            path: The path to validate.

        Returns:
            True if the resolved path is within the repository scope.
        """
        ...

    def stage(self, paths: Iterable[Path]) -> frozenset[Path]:
        """Stage files for commit.

        Args:
            paths: Absolute paths to stage. Each path is validated
                to ensure it is within the repository scope.

        Returns:
            Frozenset of staged file paths.

        Raises:
            OapsRepositoryPathViolationError: If any path is outside scope.
        """
        ...

    def discard_changes(self, paths: Sequence[Path] | None = None) -> DiscardResult:
        """Discard uncommitted changes for tracked files.

        Restores both the working tree and the index to match HEAD.
        Staged files are unstaged, and modified files are restored
        to their HEAD state. Untracked files are never touched.

        Args:
            paths: Specific files to restore (absolute paths). If None,
                restores all staged and modified files.

        Returns:
            DiscardResult containing unstaged and restored files.

        Raises:
            OapsRepositoryPathViolationError: If any path is outside scope.
        """
        ...

    def commit(
        self,
        message: str,
        *,
        staged_paths: frozenset[Path] | None = None,
    ) -> CommitResult:
        """Commit changes to the repository.

        Args:
            message: Commit message (subject line).
            staged_paths: Specific staged files to commit. If None,
                commits all currently staged files.

        Returns:
            CommitResult with commit details.

        Raises:
            OapsRepositoryConflictError: If race condition detected.
        """
        ...

    def get_last_commits(self, n: int = 10) -> list[CommitInfo]:
        """Get recent commit history.

        Args:
            n: Maximum number of commits to return. Defaults to 10.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
            Returns an empty list if the repository has no commits.
        """
        ...
