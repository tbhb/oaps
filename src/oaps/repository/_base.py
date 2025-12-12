"""Base repository abstraction for git repository management.

This module provides an abstract base class for Git repository management,
using the Template Method pattern to share common git operations while
allowing subclasses to customize repository-specific behavior.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Final, Self, cast

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from types import TracebackType

from dulwich import porcelain
from dulwich.diff_tree import tree_changes
from dulwich.index import IndexEntry, build_file_from_blob
from dulwich.object_store import tree_lookup_path
from dulwich.objects import Blob
from dulwich.repo import Repo

from oaps.exceptions import (
    OapsRepositoryConflictError,
    OapsRepositoryPathViolationError,
)
from oaps.repository._models import (
    CommitInfo,
    CommitResult,
    DiscardResult,
    RepoStatus,
)
from oaps.utils._author import get_author_info
from oaps.utils._git._common import decode_bytes

# Default identity when git config is not available.
# Note: These are also defined in _repository.py for OAPS-specific trailers.
# The duplication is intentional - _base.py uses them as author fallback,
# while _repository.py uses them for co-author trailers. Future repository
# types (e.g., ProjectRepository) may override _format_author_line() with
# different fallback behavior.
_DEFAULT_NAME: Final = "OAPS"
_DEFAULT_EMAIL: Final = "oaps@localhost"

# Git tree mode for directories (used in tree traversal)
_GIT_TREE_MODE: Final = 0o040000


class BaseRepository[StatusT: RepoStatus](ABC):
    """Abstract base class for Git repository management.

    This class provides the common infrastructure for managing Git repositories,
    including context management, status operations, staging, committing,
    and history access. Subclasses implement the Template Method hooks to
    customize repository-specific behavior.

    The class implements the context manager protocol for proper resource cleanup.
    When used as a context manager, the underlying dulwich Repo is automatically
    closed when exiting the context.

    Type Parameters:
        StatusT: The status type returned by get_status(), bound to RepoStatus.

    Attributes:
        root: The resolved path to the repository root directory.
    """

    __slots__: Final = ("_repo", "_root")
    _root: Path
    _repo: Repo

    def __init__(self, working_dir: Path | None = None) -> None:
        """Initialize the repository.

        Args:
            working_dir: The working directory to use for repository discovery.
                If None, uses the current working directory.

        Raises:
            OapsRepositoryNotInitializedError: If repository is not found.
        """
        if working_dir is None:
            working_dir = Path.cwd()
        self._root = self._discover_root(working_dir)
        self._repo = Repo(str(self._root))

    # =========================================================================
    # Abstract Methods (Template Method hooks)
    # =========================================================================

    @abstractmethod
    def _discover_root(self, working_dir: Path) -> Path:
        """Discover the repository root directory.

        Subclasses implement this to define how to locate their specific
        repository root from the given working directory.

        Args:
            working_dir: The working directory to search from.

        Returns:
            The resolved path to the repository root.

        Raises:
            OapsRepositoryNotInitializedError: If repository is not found.
        """

    @abstractmethod
    def validate_path(self, path: Path) -> bool:
        """Validate that a path is within the repository scope.

        Subclasses implement this to define their path containment rules.

        Args:
            path: The path to validate.

        Returns:
            True if the resolved path is within the repository scope.
        """

    @abstractmethod
    def _create_status(
        self,
        staged: frozenset[Path],
        modified: frozenset[Path],
        untracked: frozenset[Path],
    ) -> StatusT:
        """Create a status object for this repository type.

        Factory method for creating the appropriate status type.

        Args:
            staged: Files that are staged for commit.
            modified: Files that are modified but not staged.
            untracked: Files that are not tracked by git.

        Returns:
            A status object of the appropriate type for this repository.
        """

    # =========================================================================
    # Context Manager Protocol
    # =========================================================================

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            The repository instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and close the repository.

        Args:
            exc_type: Exception type if an exception was raised.
            exc_val: Exception value if an exception was raised.
            exc_tb: Exception traceback if an exception was raised.
        """
        self.close()

    def close(self) -> None:
        """Close the underlying git repository.

        Releases file handles held by the dulwich Repo. This method is
        automatically called when using the context manager protocol.
        """
        self._repo.close()

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def root(self) -> Path:
        """Get the resolved root path of the repository.

        Returns:
            The absolute path to the repository root directory.
        """
        return self._root

    # =========================================================================
    # Status Methods
    # =========================================================================

    def has_changes(self) -> bool:
        """Check if the repository has any uncommitted changes.

        Returns:
            True if there are staged, modified, or untracked files.

        Example:
            >>> with OapsRepository() as repo:
            ...     if repo.has_changes():
            ...         print("Repository has uncommitted changes")
        """
        status = self.get_status()
        return bool(status.staged or status.modified or status.untracked)

    def get_uncommitted_files(self) -> set[Path]:
        """Get all files with uncommitted changes.

        Returns:
            Set of absolute paths to files that are staged, modified, or untracked.

        Example:
            >>> with OapsRepository() as repo:
            ...     files = repo.get_uncommitted_files()
            ...     for f in sorted(files):
            ...         print(f.name)
        """
        status = self.get_status()
        return set(status.staged) | set(status.modified) | set(status.untracked)

    def get_status(self) -> StatusT:
        """Get the current status of the repository.

        Returns:
            Status object containing staged, modified, and untracked files.

        Example:
            >>> with OapsRepository() as repo:
            ...     status = repo.get_status()
            ...     print(f"Staged: {len(status.staged)}")
            ...     print(f"Modified: {len(status.modified)}")
            ...     print(f"Untracked: {len(status.untracked)}")
        """
        raw = porcelain.status(self._repo)

        # Extract staged files from dict with keys: 'add', 'delete', 'modify'
        staged: set[str] = set()
        staged_dict = raw.staged  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        for change_type in ("add", "delete", "modify"):
            files: list[bytes] = staged_dict.get(change_type, [])  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
            for f in files:  # pyright: ignore[reportUnknownVariableType]
                staged.add(decode_bytes(f))  # pyright: ignore[reportUnknownArgumentType]

        # Extract modified and untracked as simple list conversions
        modified = self._decode_file_list(raw.unstaged)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
        untracked = self._decode_file_list(raw.untracked)  # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]

        return self._create_status(
            staged=self._to_absolute_paths(frozenset(staged)),
            modified=self._to_absolute_paths(modified),
            untracked=self._to_absolute_paths(untracked),
        )

    # =========================================================================
    # Staging Methods
    # =========================================================================

    def stage(self, paths: Iterable[Path]) -> frozenset[Path]:
        """Stage files for commit.

        Args:
            paths: Absolute paths to stage. Each path is validated
                via validate_path() before staging.

        Returns:
            Frozenset of staged file paths.

        Raises:
            OapsRepositoryPathViolationError: If any path is outside scope.

        Example:
            >>> with OapsRepository() as repo:
            ...     spec_file = repo.root / "docs" / "specs" / "SPEC-0001.md"
            ...     staged = repo.stage([spec_file])
            ...     print(f"Staged {len(staged)} file(s)")
        """
        path_list = list(paths)
        if not path_list:
            return frozenset()

        # Validate and convert to relative paths
        relative_paths = [self._to_relative_path(p) for p in path_list]
        _ = porcelain.add(self._repo, paths=relative_paths)

        return frozenset(path_list)

    def _stage_pending(self) -> frozenset[Path]:
        """Stage all uncommitted files.

        Stages all modified and untracked files in the repository.

        Returns:
            Frozenset of staged file paths (absolute).
        """
        uncommitted = self.get_uncommitted_files()
        return self.stage(uncommitted)

    # =========================================================================
    # Commit Methods
    # =========================================================================

    def commit(
        self,
        message: str,
        *,
        staged_paths: frozenset[Path] | None = None,
    ) -> CommitResult:
        """Commit changes to the repository.

        Args:
            message: Commit message (subject line).
            staged_paths: Specific staged files to commit. If None, commits
                all currently staged files.

        Returns:
            CommitResult with commit details.

        Raises:
            OapsRepositoryConflictError: If race condition detected.

        Example:
            >>> with OapsRepository() as repo:
            ...     result = repo.commit("Update configuration")
            ...     if result.no_changes:
            ...         print("Nothing to commit")
            ...     else:
            ...         print(f"Committed {result.sha[:8]}")
        """
        # If no staged_paths provided, get current staged files
        if staged_paths is None:
            status = self.get_status()
            if not status.staged:
                return CommitResult(sha=None, files=frozenset(), no_changes=True)
            staged_paths = status.staged

        # Build message and commit
        commit_message = message.encode()
        return self._perform_commit(commit_message, staged_paths)

    def _perform_commit(
        self, message: bytes, staged_files: frozenset[Path]
    ) -> CommitResult:
        """Execute commit with race detection.

        Captures HEAD before commit and verifies that the new commit's parent
        matches the expected HEAD. This detects if another process committed
        changes between staging and committing.

        Note:
            Race detection is post-facto: the commit is written before the parent
            is validated. If a race condition is detected, the invalid commit
            already exists in the repository. Callers should be prepared to handle
            this by potentially resetting HEAD or creating a merge commit. This is
            an optimistic concurrency control pattern - the common case (no race)
            is fast, while the rare case (race detected) requires manual recovery.

        Args:
            message: Commit message as bytes.
            staged_files: Files that were staged for this commit.

        Returns:
            CommitResult with commit details.

        Raises:
            OapsRepositoryConflictError: If a race condition is detected. The
                exception's `details` attribute contains the SHA of the
                potentially invalid commit.
        """
        # Check if there's actually anything to commit
        status = self.get_status()
        if not status.staged:
            return CommitResult(sha=None, files=frozenset(), no_changes=True)

        # Capture HEAD before commit for race detection
        head_before = self._get_head_sha()

        # Get author identity
        author = self._format_author_line()

        # Perform the commit
        commit_sha_bytes: bytes = porcelain.commit(
            self._repo,
            message=message,
            author=author,
            committer=author,
        )
        commit_sha = commit_sha_bytes.hex()

        # Race detection: verify the new commit's parent matches head_before
        # This detects if another process committed between staging and commit
        # Access commit object to check parent - dulwich types are incomplete
        commit_obj = self._repo[commit_sha_bytes]
        parents: list[bytes] = getattr(commit_obj, "parents", [])
        if head_before is not None:
            # Non-empty repository: verify parent matches expected HEAD
            expected_parent = bytes.fromhex(head_before)
            if not parents or parents[0] != expected_parent:
                actual_parent = parents[0].hex() if parents else "none"
                msg = (
                    f"Concurrent modification detected: expected parent={head_before}, "
                    f"got parent={actual_parent}"
                )
                raise OapsRepositoryConflictError(
                    msg, path=self._root, details=f"Commit SHA: {commit_sha}"
                )
        elif parents:
            # Empty repository: new commit should have no parents
            msg = "Concurrent modification: expected no parent for initial commit"
            raise OapsRepositoryConflictError(
                msg, path=self._root, details=f"Commit SHA: {commit_sha}"
            )

        return CommitResult(sha=commit_sha, files=staged_files, no_changes=False)

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_head_sha(self) -> str | None:
        """Get current HEAD SHA for race detection.

        Returns:
            The HEAD commit SHA as a hex string, or None if no commits exist.
        """
        try:
            head_bytes: bytes = self._repo.head()
            return head_bytes.hex()
        except KeyError:
            # No commits yet (empty repository)
            return None

    def _format_author_line(self) -> bytes:
        """Build author/committer identity from git config.

        Tries to use the user's git identity from git config,
        falling back to "OAPS <oaps@localhost>" if not available.

        Returns:
            Author identity as bytes in "Name <email>" format.
        """
        author_info = get_author_info()
        name = author_info.name or _DEFAULT_NAME
        email = author_info.email or _DEFAULT_EMAIL
        return f"{name} <{email}>".encode()

    def _to_relative_path(self, path: Path) -> str:
        """Convert absolute path to repo-relative string.

        Args:
            path: Absolute path within the repository.

        Returns:
            Repository-relative path as string.

        Raises:
            OapsRepositoryPathViolationError: If path is outside the repository.
        """
        resolved = path.resolve()
        if not self.validate_path(resolved):
            msg = f"Path is outside repository scope: {path}"
            raise OapsRepositoryPathViolationError(msg, path=path, oaps_root=self._root)
        return str(resolved.relative_to(self._root))

    def _to_absolute_paths(self, relative_paths: frozenset[str]) -> frozenset[Path]:
        """Convert repository-relative paths to absolute paths.

        Args:
            relative_paths: Frozenset of repository-relative path strings.

        Returns:
            Frozenset of absolute Path objects.
        """
        return frozenset(self._root / p for p in relative_paths)

    def _decode_file_list(self, files: list[bytes]) -> frozenset[str]:
        """Decode a list of byte paths to a frozenset of strings.

        Args:
            files: List of file paths as bytes.

        Returns:
            Frozenset of decoded string paths.
        """
        return frozenset(decode_bytes(f) for f in files)

    # =========================================================================
    # History Methods
    # =========================================================================

    def get_last_commits(self, n: int = 10) -> list[CommitInfo]:
        """Get the most recent commits from the repository.

        Walks the commit history starting from HEAD and returns up to n
        commits in reverse chronological order. Each CommitInfo includes
        the commit SHA, message, author details, timestamp, and number
        of files changed.

        Args:
            n: Maximum number of commits to return. Defaults to 10.
                Set to a smaller value for quick history checks.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
            Returns an empty list if the repository has no commits.

        Example:
            >>> with OapsRepository() as repo:
            ...     commits = repo.get_last_commits(5)
            ...     for commit in commits:
            ...         print(f"{commit.sha[:8]} {commit.message.splitlines()[0]}")
            ...         print(f"  by {commit.author_name} on {commit.timestamp}")
        """
        head_sha = self._get_head_sha()
        if head_sha is None:
            return []

        head_bytes = bytes.fromhex(head_sha)
        walker = self._repo.get_walker(include=[head_bytes], max_entries=n)

        return [self._entry_to_commit_info(entry) for entry in walker]

    def _parse_author_line(
        self, author: bytes, author_time: int, author_tz: int
    ) -> tuple[str, str, datetime]:
        """Parse author line into name, email, and datetime.

        Args:
            author: Author bytes in "Name <email>" format.
            author_time: Unix timestamp.
            author_tz: Timezone offset in seconds (git stores as seconds WEST of UTC).

        Returns:
            Tuple of (name, email, datetime with correct timezone).
        """
        author_str = author.decode("utf-8", errors="replace")
        # Parse "Name <email>" format
        if "<" in author_str and author_str.endswith(">"):
            name_part = author_str.rsplit("<", 1)[0].strip()
            email_part = author_str.rsplit("<", 1)[1].rstrip(">")
        else:
            name_part = author_str
            email_part = ""

        # Convert timestamp to datetime with timezone
        # Git stores timezone as seconds WEST of UTC (positive = west, negative = east)
        # Python's timezone expects offset FROM UTC (positive = east, negative = west)
        # So we negate the value
        tz = timezone(timedelta(seconds=-author_tz))
        dt = datetime.fromtimestamp(author_time, tz=tz)

        return (name_part, email_part, dt)

    def _count_files_changed(self, commit_sha: bytes) -> int:
        """Count files changed in a commit.

        Compares commit tree to first parent's tree, or counts all files
        for initial commit.

        Args:
            commit_sha: The commit SHA as bytes.

        Returns:
            Number of unique files changed.
        """
        commit = self._repo[commit_sha]
        tree_sha: bytes = getattr(commit, "tree", b"")
        parents: list[bytes] = getattr(commit, "parents", [])

        if not parents:
            # Initial commit: count all files in tree
            # Walk the tree and count entries
            count = 0
            stack: list[bytes] = [tree_sha]
            while stack:
                current_tree_sha = stack.pop()
                tree_obj = self._repo[current_tree_sha]
                items_callable = getattr(tree_obj, "items", list)
                items: list[tuple[bytes, int, bytes]] = items_callable()
                for entry in items:
                    # Dulwich tree items are (name, mode, sha) - mode is position 1
                    # Handle both named tuple and regular tuple access patterns
                    mode: int = (
                        getattr(entry, "mode", entry[1])
                        if hasattr(entry, "mode")
                        else entry[1]
                    )
                    sha: bytes = (
                        getattr(entry, "sha", entry[2])
                        if hasattr(entry, "sha")
                        else entry[2]
                    )
                    if mode == _GIT_TREE_MODE:
                        stack.append(sha)
                    else:
                        count += 1
            return count
        # Compare with first parent
        parent_commit = self._repo[parents[0]]
        parent_tree: bytes = getattr(parent_commit, "tree", b"")
        changes = tree_changes(self._repo.object_store, parent_tree, tree_sha)
        return len(list(changes))

    def _entry_to_commit_info(self, entry: object) -> CommitInfo:
        """Convert a dulwich walker entry to CommitInfo.

        Args:
            entry: A WalkEntry from dulwich's get_walker().

        Returns:
            CommitInfo populated from the commit data.
        """
        commit = entry.commit  # pyright: ignore[reportAttributeAccessIssue]

        # Extract commit attributes with explicit casts (dulwich stubs incomplete)
        author_bytes = cast("bytes", commit.author)
        author_time_val = cast("int", commit.author_time)
        author_tz_val = cast("int", commit.author_timezone)
        message_bytes = cast("bytes", commit.message)
        commit_id: bytes = commit.id
        parent_list = cast("list[bytes]", commit.parents)

        # Parse author
        author_name, author_email, timestamp = self._parse_author_line(
            author_bytes,
            author_time_val,
            author_tz_val,
        )

        # Get message
        message_str = message_bytes.decode("utf-8", errors="replace")

        # Count files changed
        files_changed = self._count_files_changed(commit_id)

        # Get parent SHAs
        parent_shas = tuple(p.hex() for p in parent_list)

        return CommitInfo(
            sha=commit_id.hex(),
            message=message_str,
            author_name=author_name,
            author_email=author_email,
            timestamp=timestamp,
            files_changed=files_changed,
            parent_shas=parent_shas,
        )

    # =========================================================================
    # Discard Methods
    # =========================================================================

    def discard_changes(self, paths: Sequence[Path] | None = None) -> DiscardResult:
        """Discard uncommitted changes for tracked files.

        Restores both the working tree and the index to match HEAD. Staged
        files are unstaged, and modified files are restored to their HEAD
        state. Untracked files are never touched by this operation.

        Note:
            Index and working tree operations are not atomic. The index is
            updated first, then working tree files are restored. If file
            restoration fails (e.g., permission denied, disk full), the index
            will already be updated but some files may not be restored. In
            this case, `restored` will only contain successfully restored
            files, allowing callers to detect partial failure by comparing
            `len(unstaged)` with `len(restored)`.

        Args:
            paths: Specific files to restore (absolute paths). If None,
                restores all staged and modified files. Only files that are
                actually staged or modified will be affected.

        Returns:
            DiscardResult containing:
                - unstaged: Files that were removed from the staging area
                - restored: Files restored to their HEAD state in working tree
                - no_changes: True if nothing was discarded

        Raises:
            OapsRepositoryPathViolationError: If any path resolves outside
                the repository scope (including via symlinks).

        Example:
            >>> with repo:
            ...     # Discard all uncommitted changes
            ...     result = repo.discard_changes()
            ...     print(f"Unstaged {len(result.unstaged)} files")
            ...     print(f"Restored {len(result.restored)} files")
            ...
            ...     # Discard changes to specific files only
            ...     spec_file = repo.root / "docs" / "specs" / "SPEC-0001.md"
            ...     result = repo.discard_changes([spec_file])
        """
        # Handle empty repository
        tree_sha = self._get_head_tree()
        if tree_sha is None:
            return DiscardResult(
                unstaged=frozenset(),
                restored=frozenset(),
                no_changes=True,
            )

        # Get current status to identify files to discard
        status = self.get_status()

        if paths is None:
            # Discard all tracked changes
            target_staged = set(status.staged)
            target_modified = set(status.modified)
        else:
            # Validate and filter to specified paths
            validated_paths: set[Path] = set()
            for p in paths:
                if not self.validate_path(p):
                    msg = f"Path is outside repository scope: {p}"
                    raise OapsRepositoryPathViolationError(
                        msg, path=p, oaps_root=self._root
                    )
                validated_paths.add(p.resolve())

            target_staged = validated_paths & set(status.staged)
            target_modified = validated_paths & set(status.modified)

        all_targets = target_staged | target_modified

        if not all_targets:
            return DiscardResult(
                unstaged=frozenset(),
                restored=frozenset(),
                no_changes=True,
            )

        # Convert to relative paths for tree operations
        relative_paths = [self._to_relative_path(p) for p in all_targets]

        # Update index from HEAD tree (unstages staged files, resets modified)
        self._update_index_from_tree(tree_sha, relative_paths)

        # Restore working tree files from HEAD
        restored: set[Path] = set()
        for rel_path in relative_paths:
            abs_path = self._root / rel_path
            if self._restore_file_from_tree(tree_sha, rel_path):
                restored.add(abs_path)

        return DiscardResult(
            unstaged=frozenset(target_staged),
            restored=frozenset(restored),
            no_changes=False,
        )

    def _get_head_tree(self) -> bytes | None:
        """Get the tree SHA for HEAD commit.

        Returns:
            Tree SHA as bytes, or None if no commits exist.
        """
        head_sha = self._get_head_sha()
        if head_sha is None:
            return None
        head_bytes = bytes.fromhex(head_sha)
        commit_obj = self._repo[head_bytes]
        tree: bytes | None = getattr(commit_obj, "tree", None)
        return tree

    def _restore_file_from_tree(self, tree_sha: bytes, relative_path: str) -> bool:
        """Restore a single file from a tree to working directory.

        Args:
            tree_sha: The tree SHA to restore from.
            relative_path: Repository-relative path string.

        Returns:
            True if file was restored, False if file not in tree.
        """
        path_bytes = relative_path.encode("utf-8")
        try:
            mode, blob_sha = tree_lookup_path(
                self._repo.__getitem__, tree_sha, path_bytes
            )
        except KeyError:
            # File not in tree
            return False

        blob = self._repo[blob_sha]
        target_path = self._root / relative_path

        # Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file from blob (cast needed due to dulwich's incomplete type stubs)
        if isinstance(blob, Blob):
            _ = build_file_from_blob(blob, mode, str(target_path).encode("utf-8"))

        return True

    def _update_index_from_tree(
        self, tree_sha: bytes, relative_paths: list[str]
    ) -> None:
        """Update index entries from tree for specified paths.

        For files in tree: set index entry to match tree.
        For files not in tree: remove from index (unstage newly added files).

        Args:
            tree_sha: The tree SHA to read entries from.
            relative_paths: List of repository-relative paths.
        """
        index = self._repo.open_index()

        try:
            for rel_path in relative_paths:
                path_bytes = rel_path.encode("utf-8")
                try:
                    mode, blob_sha = tree_lookup_path(
                        self._repo.__getitem__, tree_sha, path_bytes
                    )
                    # File exists in tree - update index entry
                    blob = self._repo[blob_sha]
                    target_file = self._root / rel_path
                    if target_file.exists():
                        stat_info = target_file.stat()
                        # Get blob data size (dulwich type stubs incomplete)
                        blob_data: bytes = getattr(blob, "data", b"")
                        # Create index entry using dulwich IndexEntry
                        # ctime/mtime are tuples of (seconds, nanoseconds)
                        index[path_bytes] = IndexEntry(
                            ctime=(
                                int(stat_info.st_ctime),
                                stat_info.st_ctime_ns % 1_000_000_000,
                            ),
                            mtime=(
                                int(stat_info.st_mtime),
                                stat_info.st_mtime_ns % 1_000_000_000,
                            ),
                            dev=stat_info.st_dev,
                            ino=stat_info.st_ino,
                            mode=mode,
                            uid=stat_info.st_uid,
                            gid=stat_info.st_gid,
                            size=len(blob_data),
                            sha=blob_sha,
                            flags=0,
                        )
                except KeyError:
                    # File not in tree - remove from index (was newly added)
                    if path_bytes in index:
                        del index[path_bytes]
        finally:
            index.write()
