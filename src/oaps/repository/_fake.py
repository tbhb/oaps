# ruff: noqa: TC003  # Path and datetime needed at runtime for dataclass fields
"""Fake repository for testing.

This module provides a FakeRepository class that implements RepositoryProtocol
for use in tests without requiring an actual Git repository.
"""

# Iterable and Sequence needed at runtime for method signatures
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from oaps.repository._models import (
    BlameLine,
    CommitInfo,
    CommitResult,
    DiffStats,
    DiscardResult,
    FileDiffStats,
)


@dataclass(slots=True)
class FakeRepository:
    """Fake Git repository for testing.

    Implements RepositoryProtocol and the extended methods from ProjectRepository
    without requiring an actual Git repository. Useful for unit testing code that
    depends on repository operations.

    The fake maintains internal state that can be manipulated for testing:
    - staged/modified/untracked sets track file status
    - commits list tracks commit history
    - Helper methods allow setting up specific test scenarios

    Example:
        >>> repo = FakeRepository()
        >>> repo.modified.add(Path("/fake/project/src/main.py"))
        >>> assert repo.has_changes() is True
        >>> staged = repo.stage([Path("/fake/project/src/main.py")])
        >>> result = repo.commit("Fix bug")
        >>> assert result.no_changes is False
    """

    root: Path = field(default_factory=lambda: Path("/fake/project"))
    staged: set[Path] = field(default_factory=set)
    modified: set[Path] = field(default_factory=set)
    untracked: set[Path] = field(default_factory=set)
    commits: list[CommitInfo] = field(default_factory=list)
    _commit_counter: int = field(default=0)
    _diff_content: str = field(default="")
    _blame_lines: dict[Path, list[BlameLine]] = field(default_factory=dict)
    _file_history: dict[tuple[Path, str], bytes] = field(default_factory=dict)

    # =========================================================================
    # Context Manager Protocol
    # =========================================================================

    def __enter__(self) -> Self:
        """Enter context manager.

        Returns:
            Self for use in with statement.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.
        """
        self.close()

    # =========================================================================
    # RepositoryProtocol Methods
    # =========================================================================

    def close(self) -> None:
        """Close the repository (no-op for fake)."""

    def has_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if there are staged, modified, or untracked files.
        """
        return bool(self.staged or self.modified or self.untracked)

    def get_uncommitted_files(self) -> set[Path]:
        """Get all files with uncommitted changes.

        Returns:
            Set of absolute paths to files that are staged, modified,
            or untracked.
        """
        return self.staged | self.modified | self.untracked

    def validate_path(self, path: Path) -> bool:
        """Check if path is within this repository's scope.

        A path is valid if it resolves to a location within the repository
        root AND is not within a .oaps/ directory.

        Args:
            path: The path to validate.

        Returns:
            True if the resolved path is within the repository scope
            and not in .oaps/.
        """
        resolved = path.resolve()

        # Must be inside root
        if not resolved.is_relative_to(self.root):
            return False

        # Must not contain .oaps in any path component
        return ".oaps" not in resolved.parts

    def stage(self, paths: Iterable[Path]) -> frozenset[Path]:
        """Stage files for commit.

        Args:
            paths: Absolute paths to stage.

        Returns:
            Frozenset of staged file paths.
        """
        staged_paths: set[Path] = set()
        for path in paths:
            if self.validate_path(path):
                self.staged.add(path)
                self.modified.discard(path)
                self.untracked.discard(path)
                staged_paths.add(path)
        return frozenset(staged_paths)

    def discard_changes(self, paths: Sequence[Path] | None = None) -> DiscardResult:
        """Discard uncommitted changes for tracked files.

        Args:
            paths: Specific files to restore (absolute paths). If None,
                restores all staged and modified files.

        Returns:
            DiscardResult containing unstaged and restored files.
        """
        if paths is None:
            # Discard all changes
            unstaged = frozenset(self.staged)
            restored = frozenset(self.modified)
            self.staged.clear()
            self.modified.clear()
        else:
            # Discard specific files
            unstaged_set: set[Path] = set()
            restored_set: set[Path] = set()
            for path in paths:
                if path in self.staged:
                    self.staged.discard(path)
                    unstaged_set.add(path)
                if path in self.modified:
                    self.modified.discard(path)
                    restored_set.add(path)
            unstaged = frozenset(unstaged_set)
            restored = frozenset(restored_set)

        return DiscardResult(
            unstaged=unstaged,
            restored=restored,
            no_changes=not unstaged and not restored,
        )

    def commit(
        self,
        message: str,
        *,
        staged_paths: frozenset[Path] | None = None,
    ) -> CommitResult:
        """Commit changes to the repository.

        Args:
            message: Commit message.
            staged_paths: Specific staged files to commit. If None,
                commits all currently staged files.

        Returns:
            CommitResult with commit details.
        """
        # Determine files to commit
        if staged_paths is None:
            files_to_commit = frozenset(self.staged)
        else:
            # Only commit files that are actually staged
            files_to_commit = staged_paths & frozenset(self.staged)

        if not files_to_commit:
            return CommitResult(sha=None, files=frozenset(), no_changes=True)

        # Generate SHA
        self._commit_counter += 1
        sha = f"fake{self._commit_counter:08x}"

        # Determine parent SHAs
        parent_shas: tuple[str, ...] = ()
        if self.commits:
            parent_shas = (self.commits[0].sha,)

        # Create commit info
        commit_info = CommitInfo(
            sha=sha,
            message=message,
            author_name="Fake Author",
            author_email="fake@example.com",
            timestamp=datetime.now(UTC),
            files_changed=len(files_to_commit),
            parent_shas=parent_shas,
        )

        # Update state
        self.commits.insert(0, commit_info)  # Newest first
        for path in files_to_commit:
            self.staged.discard(path)

        return CommitResult(sha=sha, files=files_to_commit, no_changes=False)

    def get_last_commits(self, n: int = 10) -> list[CommitInfo]:
        """Get recent commit history.

        Args:
            n: Maximum number of commits to return.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
        """
        return self.commits[:n]

    # =========================================================================
    # Extended Methods (matching ProjectRepository)
    # =========================================================================

    def get_diff(self, *, staged: bool = False, context_lines: int = 3) -> str:
        """Get unified diff of uncommitted changes.

        Args:
            staged: If True, show staged changes. If False, show unstaged changes.
            context_lines: Number of context lines (ignored in fake).

        Returns:
            Configured diff content string, or empty string if not set.
        """
        # context_lines accepted for API compatibility
        _ = context_lines
        _ = staged
        return self._diff_content

    def get_diff_stats(self, *, staged: bool = False) -> DiffStats:
        """Get structured diff statistics.

        Returns stats calculated from staged or modified sets.
        Each file gets 1 addition, 0 deletions for simplicity.

        Note:
            The `is_new` flag may not be accurate for staged files since
            `stage()` removes files from `untracked`. For accurate `is_new`
            tracking, configure the fake state directly before calling this method.

        Args:
            staged: If True, analyze staged changes. If False, analyze unstaged.

        Returns:
            DiffStats with per-file and aggregate statistics.
        """
        files = self.staged if staged else self.modified
        file_stats = tuple(
            FileDiffStats(
                path=str(f.relative_to(self.root))
                if f.is_relative_to(self.root)
                else str(f),
                additions=1,
                deletions=0,
                is_new=f in self.untracked,
            )
            for f in files
        )

        return DiffStats(
            files=file_stats,
            total_additions=len(file_stats),
            total_deletions=0,
            files_changed=len(file_stats),
        )

    def get_log(
        self,
        n: int = 10,
        *,
        path: Path | None = None,
        grep: str | None = None,
        author: str | None = None,
    ) -> list[CommitInfo]:
        """Get commit log with optional filters.

        Args:
            n: Maximum number of commits to return.
            path: Filter to commits affecting this path (ignored in fake).
            grep: Case-insensitive substring to search for in commit messages.
            author: Case-insensitive substring to match against author name or email.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
        """
        # path filter not implemented in fake (would require tracking files per commit)
        _ = path

        result: list[CommitInfo] = []
        for commit in self.commits:
            if len(result) >= n:
                break

            # Apply grep filter
            if grep is not None and grep.lower() not in commit.message.lower():
                continue

            # Apply author filter
            if author is not None:
                author_lower = author.lower()
                if (
                    author_lower not in commit.author_name.lower()
                    and author_lower not in commit.author_email.lower()
                ):
                    continue

            result.append(commit)

        return result

    def get_blame(
        self,
        path: Path,
        *,
        max_commits: int | None = 100,
    ) -> list[BlameLine]:
        """Get blame attribution for each line of a file.

        Args:
            path: Path to the file to blame.
            max_commits: Reserved for API compatibility (ignored in fake).

        Returns:
            List of BlameLine in line order, or empty list if not configured.
        """
        _ = max_commits
        return self._blame_lines.get(path, [])

    def search_commits(
        self,
        *,
        grep: str | None = None,
        author: str | None = None,
        max_entries: int = 1000,
        use_git_cli: bool = False,
    ) -> list[CommitInfo]:
        """Search commit history with optional filters.

        Args:
            grep: Case-insensitive substring to search for in commit messages.
            author: Case-insensitive substring to match against author name or email.
            max_entries: Maximum number of commits to return.
            use_git_cli: Reserved for API compatibility (ignored in fake).

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
        """
        _ = use_git_cli
        return self.get_log(n=max_entries, grep=grep, author=author)

    def get_file_at_commit(
        self,
        path: Path,
        commit: str,
    ) -> bytes | None:
        """Get file contents at a specific commit.

        Args:
            path: Path to the file.
            commit: Commit SHA.

        Returns:
            File contents as bytes, or None if not configured.
        """
        return self._file_history.get((path, commit))

    # =========================================================================
    # Test Helper Methods
    # =========================================================================

    def set_diff(self, content: str) -> None:
        """Set the diff content returned by get_diff().

        Args:
            content: Diff content string to return.
        """
        self._diff_content = content

    def set_blame(self, path: Path, lines: list[BlameLine]) -> None:
        """Set blame lines for a specific file.

        Args:
            path: Path to the file.
            lines: List of BlameLine objects to return for this file.
        """
        self._blame_lines[path] = lines

    def set_file_at_commit(self, path: Path, commit: str, content: bytes) -> None:
        """Set file content at a specific commit.

        Args:
            path: Path to the file.
            commit: Commit SHA.
            content: File content as bytes.
        """
        self._file_history[(path, commit)] = content
