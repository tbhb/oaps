# ruff: noqa: TC003  # Path needed at runtime for method bodies
"""Project repository management.

This module provides the ProjectRepository class for managing the main
project Git repository while excluding OAPS internal files.
"""

import subprocess
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING, cast, override

from dulwich import porcelain
from dulwich.diff_tree import (
    CHANGE_ADD,
    CHANGE_DELETE,
    CHANGE_RENAME,
    RenameDetector,
    tree_changes,
)
from dulwich.index import commit_tree
from dulwich.object_store import tree_lookup_path
from dulwich.patch import is_binary, unified_diff

from oaps.exceptions import (
    OapsRepositoryPathViolationError,
    ProjectRepositoryNotInitializedError,
)
from oaps.repository._base import BaseRepository
from oaps.repository._models import (
    BlameLine,
    CommitInfo,
    DiffStats,
    FileDiffStats,
    ProjectRepoStatus,
)
from oaps.utils._git._common import decode_bytes

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dulwich.diff_tree import TreeChange

# Similarity threshold for rename detection (0-100 scale for dulwich)
_RENAME_THRESHOLD: int = 60

# Git SHA length in hexadecimal characters
_SHA_HEX_LENGTH: int = 40

# Minimum parts in blame header line: <sha> <orig> <final>
_MIN_BLAME_HEADER_PARTS: int = 3

# Git timezone string length (+HHMM or -HHMM)
_TZ_STRING_LENGTH: int = 5

# Minimum length for abbreviated SHA resolution
_MIN_SHA_ABBREV_LENGTH: int = 4

# Default max entries for search_commits
_DEFAULT_SEARCH_MAX_ENTRIES: int = 1000

# Overscan multiplier for filtered searches
_FILTER_OVERSCAN_MULTIPLIER: int = 10


class ProjectRepository(BaseRepository[ProjectRepoStatus]):
    """Manages the project Git repository, excluding .oaps/ directory.

    This class provides access to the git repository for the main project,
    with path validation that ensures .oaps/ internal files are never
    included in operations. It is worktree-aware and can be initialized
    from any worktree in the project.

    The class implements the context manager protocol for proper resource cleanup.
    When used as a context manager, the underlying dulwich Repo is automatically
    closed when exiting the context.

    Attributes:
        root: The resolved path to the project repository root.

    Example:
        with ProjectRepository() as repo:
            status = repo.get_status()
            print(f"Staged files: {status.staged}")
            # Will not include any files from .oaps/
    """

    # Note: Additional instance attributes are stored in __dict__ since BaseRepository
    # declares __slots__ as Final. This slightly increases memory usage but maintains
    # type safety.
    _oaps_dir: Path
    _oaps_dir_name: str

    def __init__(
        self,
        worktree_dir: Path | None = None,
        oaps_dir_name: str = ".oaps",
    ) -> None:
        """Initialize the project repository.

        Args:
            worktree_dir: The working directory to discover from. If None,
                uses the current working directory.
            oaps_dir_name: Name of the OAPS directory to exclude from
                operations. Defaults to ".oaps". Configurable for testing.

        Raises:
            ProjectRepositoryNotInitializedError: If no Git repository
                is found at or above the working directory.
        """
        self._oaps_dir_name = oaps_dir_name
        # _oaps_dir is set in _discover_root before super().__init__ opens the repo
        super().__init__(working_dir=worktree_dir)

    # =========================================================================
    # Abstract Method Implementations
    # =========================================================================

    @override
    def _discover_root(self, working_dir: Path) -> Path:
        """Discover project Git repository root.

        Walks up the directory tree from working_dir until a .git directory
        or file is found. Git worktrees use a .git file pointing to the
        main repository, so both cases are handled.

        Args:
            working_dir: The directory to start discovery from.

        Returns:
            The resolved path to the project repository root.

        Raises:
            ProjectRepositoryNotInitializedError: If no .git is found
                in working_dir or any of its ancestors.
        """
        current = working_dir.resolve()

        while True:
            git_path = current / ".git"
            if git_path.exists():
                # Found project root - set _oaps_dir before returning
                self._oaps_dir = (current / self._oaps_dir_name).resolve()
                return current

            parent = current.parent
            if parent == current:
                # Reached filesystem root without finding .git
                msg = f"Not inside a Git repository: {working_dir}"
                raise ProjectRepositoryNotInitializedError(msg, path=working_dir)
            current = parent

    @override
    def validate_path(self, path: Path) -> bool:
        """Validate that a path is within the project but not in .oaps/.

        Paths are valid if they resolve to a location within the project
        repository root AND are not within the .oaps/ directory. This
        prevents accidental modification of OAPS internal files.

        Args:
            path: The path to validate.

        Returns:
            True if the resolved path is within the project root and
            not within .oaps/.
        """
        resolved = path.resolve()

        # Must be inside project root
        if not resolved.is_relative_to(self._root):
            return False

        # Must NOT be inside .oaps/ directory (even if it doesn't exist yet)
        return not resolved.is_relative_to(self._oaps_dir)

    @override
    def _create_status(
        self,
        staged: frozenset[Path],
        modified: frozenset[Path],
        untracked: frozenset[Path],
    ) -> ProjectRepoStatus:
        """Create ProjectRepoStatus instance.

        Args:
            staged: Files that are staged for commit.
            modified: Files that are modified but not staged.
            untracked: Files that are not tracked by git.

        Returns:
            ProjectRepoStatus with the given file sets.
        """
        return ProjectRepoStatus(
            staged=staged,
            modified=modified,
            untracked=untracked,
        )

    # =========================================================================
    # Diff Methods
    # =========================================================================

    def get_diff(self, *, staged: bool = False, context_lines: int = 3) -> str:
        """Get unified diff of uncommitted changes.

        Args:
            staged: If True, show staged changes (HEAD vs index).
                If False, show unstaged changes (index vs working tree).
            context_lines: Number of context lines around changes (default 3).

        Returns:
            Raw unified diff string, or empty string if no changes.

        Example:
            >>> repo = ProjectRepository()
            >>> diff = repo.get_diff()
            >>> print(diff)
            diff --git a/src/main.py b/src/main.py
            --- a/src/main.py
            +++ b/src/main.py
            @@ -1,3 +1,4 @@
            +# New comment
             def main():
                 pass
        """
        if staged:
            return self._get_staged_diff(context_lines)
        return self._get_unstaged_diff(context_lines)

    def get_diff_stats(self, *, staged: bool = False) -> DiffStats:
        """Get structured diff statistics.

        Args:
            staged: If True, analyze staged changes.
                If False, analyze unstaged changes.

        Returns:
            DiffStats with per-file and aggregate statistics.

        Example:
            >>> repo = ProjectRepository()
            >>> stats = repo.get_diff_stats()
            >>> adds, dels = stats.total_additions, stats.total_deletions
            >>> print(f"{stats.files_changed} files, +{adds}, -{dels}")
            3 files, +25, -10
        """
        if staged:
            return self._get_staged_diff_stats()
        return self._get_unstaged_diff_stats()

    # =========================================================================
    # Private Diff Helpers
    # =========================================================================

    def _is_oaps_path(self, path_str: str) -> bool:
        """Check if a path string is within the OAPS directory.

        Args:
            path_str: Repository-relative path string.

        Returns:
            True if path is within the OAPS directory.
        """
        return (
            path_str.startswith(self._oaps_dir_name + "/")
            or path_str == self._oaps_dir_name
        )

    def _get_index_tree_sha(self) -> bytes:
        """Build a tree SHA from the current index.

        Returns:
            Tree SHA bytes representing the current index state.
        """
        from dulwich.index import IndexEntry as _IndexEntry  # noqa: PLC0415

        index = self._repo.open_index()
        blobs: list[tuple[bytes, bytes, int]] = []
        for path, entry in index.items():
            # Skip conflicted entries (they don't have sha/mode attributes)
            if isinstance(entry, _IndexEntry):
                blobs.append((path, entry.sha, entry.mode))
        return commit_tree(self._repo.object_store, blobs)

    def _get_blob_content(self, sha: bytes) -> bytes:
        """Get the content of a blob by SHA.

        Args:
            sha: Blob SHA.

        Returns:
            Blob content as bytes.
        """
        blob = self._repo[sha]
        data: bytes = getattr(blob, "data", b"")
        return data

    def _get_staged_diff(self, context_lines: int) -> str:
        """Generate unified diff for staged changes (HEAD vs index).

        Args:
            context_lines: Number of context lines around changes.

        Returns:
            Unified diff string.
        """
        head_tree = self._get_head_tree()
        index_tree = self._get_index_tree_sha()

        # Use rename detector for staged diffs
        rename_detector = RenameDetector(
            self._repo.object_store,
            rename_threshold=_RENAME_THRESHOLD,
        )

        changes = tree_changes(
            self._repo.object_store,
            head_tree,
            index_tree,
            rename_detector=rename_detector,
        )

        diff_parts: list[str] = []
        for change in changes:
            diff_text = self._format_tree_change_diff(change, context_lines)
            if diff_text:
                diff_parts.append(diff_text)

        return "".join(diff_parts)

    def _get_unstaged_diff(self, context_lines: int) -> str:
        """Generate unified diff for unstaged changes (index vs working tree).

        Args:
            context_lines: Number of context lines around changes.

        Returns:
            Unified diff string.
        """
        from dulwich.index import IndexEntry as _IndexEntry  # noqa: PLC0415

        # Get modified (unstaged) files from status
        raw = porcelain.status(self._repo)
        modified_bytes: list[bytes] = raw.unstaged  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]

        diff_parts: list[str] = []
        index = self._repo.open_index()

        for item in modified_bytes:  # pyright: ignore[reportUnknownVariableType]
            path_bytes: bytes = item  # pyright: ignore[reportUnknownVariableType]
            path_str = decode_bytes(path_bytes)  # pyright: ignore[reportUnknownArgumentType]

            # Skip OAPS paths
            if self._is_oaps_path(path_str):
                continue

            # Get index content
            if path_bytes not in index:
                continue

            entry = index[path_bytes]
            # Skip conflicted entries
            if not isinstance(entry, _IndexEntry):
                continue
            index_content = self._get_blob_content(entry.sha)

            # Get working tree content
            working_path = self._root / path_str
            if not working_path.exists():
                # File was deleted in working tree
                working_content = b""
            else:
                try:
                    working_content = working_path.read_bytes()
                except OSError:
                    continue

            # Check for binary
            if is_binary(index_content) or is_binary(working_content):
                binary_header = f"diff --git a/{path_str} b/{path_str}\n"
                binary_msg = f"Binary files a/{path_str} and b/{path_str} differ\n"
                diff_parts.append(binary_header + binary_msg)
                continue

            # Generate unified diff
            diff_text = self._generate_unified_diff(
                index_content,
                working_content,
                f"a/{path_str}",
                f"b/{path_str}",
                context_lines,
            )
            if diff_text:
                diff_parts.append(f"diff --git a/{path_str} b/{path_str}\n{diff_text}")

        return "".join(diff_parts)

    def _format_tree_change_diff(
        self,
        change: TreeChange,
        context_lines: int,
    ) -> str:
        """Format a TreeChange as a unified diff.

        Args:
            change: TreeChange from tree_changes.
            context_lines: Number of context lines.

        Returns:
            Formatted diff string, or empty string if path should be filtered.
        """
        # Get paths from change
        old_path_bytes: bytes | None = change.old.path if change.old else None
        new_path_bytes: bytes | None = change.new.path if change.new else None

        old_path_str = decode_bytes(old_path_bytes) if old_path_bytes else None
        new_path_str = decode_bytes(new_path_bytes) if new_path_bytes else None

        # Filter OAPS paths
        if old_path_str and self._is_oaps_path(old_path_str):
            return ""
        if new_path_str and self._is_oaps_path(new_path_str):
            return ""

        # Get content
        old_content = b""
        new_content = b""

        if change.old and change.old.sha:
            old_content = self._get_blob_content(change.old.sha)
        if change.new and change.new.sha:
            new_content = self._get_blob_content(change.new.sha)

        # Determine display paths
        if change.type == CHANGE_RENAME:
            from_path = f"a/{old_path_str}"
            to_path = f"b/{new_path_str}"
            header = f"diff --git a/{old_path_str} b/{new_path_str}\n"
            header += f"rename from {old_path_str}\n"
            header += f"rename to {new_path_str}\n"
        elif change.type == CHANGE_ADD:
            from_path = "/dev/null"
            to_path = f"b/{new_path_str}"
            header = f"diff --git a/{new_path_str} b/{new_path_str}\n"
            header += "new file mode 100644\n"
        elif change.type == CHANGE_DELETE:
            from_path = f"a/{old_path_str}"
            to_path = "/dev/null"
            header = f"diff --git a/{old_path_str} b/{old_path_str}\n"
            header += "deleted file mode 100644\n"
        else:
            # CHANGE_MODIFY
            path_str = new_path_str or old_path_str or ""
            from_path = f"a/{path_str}"
            to_path = f"b/{path_str}"
            header = f"diff --git a/{path_str} b/{path_str}\n"

        # Check for binary
        if is_binary(old_content) or is_binary(new_content):
            return header + "Binary files differ\n"

        # Generate unified diff
        diff_text = self._generate_unified_diff(
            old_content,
            new_content,
            from_path,
            to_path,
            context_lines,
        )

        if not diff_text:
            return ""

        return header + diff_text

    def _generate_unified_diff(
        self,
        old_content: bytes,
        new_content: bytes,
        from_file: str,
        to_file: str,
        context_lines: int,
    ) -> str:
        """Generate unified diff between two content blobs.

        Args:
            old_content: Original content as bytes.
            new_content: New content as bytes.
            from_file: Source file path for diff header.
            to_file: Target file path for diff header.
            context_lines: Number of context lines.

        Returns:
            Unified diff string.
        """
        # Split into lines, preserving line endings
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Generate diff using dulwich's unified_diff
        diff_lines = unified_diff(
            old_lines,
            new_lines,
            fromfile=from_file.encode(),
            tofile=to_file.encode(),
            n=context_lines,
        )

        # Join diff lines - unified_diff yields bytes
        result_parts: list[str] = [
            line.decode("utf-8", errors="replace") for line in diff_lines
        ]

        return "".join(result_parts)

    def _get_staged_diff_stats(self) -> DiffStats:
        """Get diff statistics for staged changes.

        Returns:
            DiffStats with per-file statistics.
        """
        head_tree = self._get_head_tree()
        index_tree = self._get_index_tree_sha()

        # Use rename detector
        rename_detector = RenameDetector(
            self._repo.object_store,
            rename_threshold=_RENAME_THRESHOLD,
        )

        changes = tree_changes(
            self._repo.object_store,
            head_tree,
            index_tree,
            rename_detector=rename_detector,
        )

        file_stats: list[FileDiffStats] = []
        total_additions = 0
        total_deletions = 0

        for change in changes:
            stats = self._compute_tree_change_stats(change)
            if stats is not None:
                file_stats.append(stats)
                total_additions += stats.additions
                total_deletions += stats.deletions

        return DiffStats(
            files=tuple(file_stats),
            total_additions=total_additions,
            total_deletions=total_deletions,
            files_changed=len(file_stats),
        )

    def _get_unstaged_diff_stats(self) -> DiffStats:
        """Get diff statistics for unstaged changes.

        Returns:
            DiffStats with per-file statistics.
        """
        from dulwich.index import IndexEntry as _IndexEntry  # noqa: PLC0415

        raw = porcelain.status(self._repo)
        modified_bytes: list[bytes] = raw.unstaged  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]

        file_stats: list[FileDiffStats] = []
        total_additions = 0
        total_deletions = 0
        index = self._repo.open_index()

        for item in modified_bytes:  # pyright: ignore[reportUnknownVariableType]
            path_bytes: bytes = item  # pyright: ignore[reportUnknownVariableType]
            path_str = decode_bytes(path_bytes)  # pyright: ignore[reportUnknownArgumentType]

            # Skip OAPS paths
            if self._is_oaps_path(path_str):
                continue

            # Get index content
            if path_bytes not in index:
                continue

            entry = index[path_bytes]
            # Skip conflicted entries
            if not isinstance(entry, _IndexEntry):
                continue
            index_content = self._get_blob_content(entry.sha)

            # Get working tree content
            working_path = self._root / path_str
            is_deleted = not working_path.exists()

            if is_deleted:
                working_content = b""
            else:
                try:
                    working_content = working_path.read_bytes()
                except OSError:
                    continue

            # Check for binary
            content_is_binary = is_binary(index_content) or is_binary(working_content)

            if content_is_binary:
                file_stats.append(
                    FileDiffStats(
                        path=path_str,
                        additions=0,
                        deletions=0,
                        is_binary=True,
                        is_deleted=is_deleted,
                    )
                )
                continue

            # Compute line stats
            additions, deletions = self._compute_line_stats(
                index_content, working_content
            )
            total_additions += additions
            total_deletions += deletions

            file_stats.append(
                FileDiffStats(
                    path=path_str,
                    additions=additions,
                    deletions=deletions,
                    is_deleted=is_deleted,
                )
            )

        return DiffStats(
            files=tuple(file_stats),
            total_additions=total_additions,
            total_deletions=total_deletions,
            files_changed=len(file_stats),
        )

    def _compute_tree_change_stats(self, change: TreeChange) -> FileDiffStats | None:
        """Compute diff statistics for a TreeChange.

        Args:
            change: TreeChange from tree_changes.

        Returns:
            FileDiffStats or None if path should be filtered.
        """
        # Get paths
        old_path_bytes: bytes | None = change.old.path if change.old else None
        new_path_bytes: bytes | None = change.new.path if change.new else None

        old_path_str = decode_bytes(old_path_bytes) if old_path_bytes else None
        new_path_str = decode_bytes(new_path_bytes) if new_path_bytes else None

        # Filter OAPS paths
        if old_path_str and self._is_oaps_path(old_path_str):
            return None
        if new_path_str and self._is_oaps_path(new_path_str):
            return None

        # Determine display path and flags
        is_new = change.type == CHANGE_ADD
        is_deleted = change.type == CHANGE_DELETE
        is_renamed = change.type == CHANGE_RENAME

        # Use new path for display (or old path for deletions)
        display_path = new_path_str or old_path_str or ""

        # Get content
        old_content = b""
        new_content = b""

        if change.old and change.old.sha:
            old_content = self._get_blob_content(change.old.sha)
        if change.new and change.new.sha:
            new_content = self._get_blob_content(change.new.sha)

        # Check for binary
        content_is_binary = is_binary(old_content) or is_binary(new_content)

        if content_is_binary:
            return FileDiffStats(
                path=display_path,
                additions=0,
                deletions=0,
                is_binary=True,
                is_new=is_new,
                is_deleted=is_deleted,
                is_renamed=is_renamed,
                old_path=old_path_str if is_renamed else None,
            )

        # Compute line stats
        additions, deletions = self._compute_line_stats(old_content, new_content)

        return FileDiffStats(
            path=display_path,
            additions=additions,
            deletions=deletions,
            is_new=is_new,
            is_deleted=is_deleted,
            is_renamed=is_renamed,
            old_path=old_path_str if is_renamed else None,
        )

    def _compute_line_stats(
        self,
        old_content: bytes,
        new_content: bytes,
    ) -> tuple[int, int]:
        """Compute additions and deletions between two content blobs.

        Uses SequenceMatcher to compute the diff and count changed lines.

        Args:
            old_content: Original content.
            new_content: New content.

        Returns:
            Tuple of (additions, deletions).
        """
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        matcher = SequenceMatcher(None, old_lines, new_lines)

        additions = 0
        deletions = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                deletions += i2 - i1
            elif tag == "insert":
                additions += j2 - j1
            elif tag == "replace":
                deletions += i2 - i1
                additions += j2 - j1
            # "equal" - no changes

        return additions, deletions

    # =========================================================================
    # Log Methods
    # =========================================================================

    def get_log(
        self,
        n: int = 10,
        *,
        path: Path | None = None,
        grep: str | None = None,
        author: str | None = None,
    ) -> list[CommitInfo]:
        """Get commit log with optional filters.

        Retrieves commit history from HEAD with support for filtering by path,
        message content, and author. Filters combine with AND logic when multiple
        are specified.

        Args:
            n: Maximum number of commits to return. Defaults to 10.
            path: Filter to commits affecting this path. Accepts absolute paths
                (converted to repo-relative) or repo-relative paths.
            grep: Case-insensitive substring to search for in commit messages.
            author: Case-insensitive substring to match against author name or email.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
            Returns an empty list if no commits exist or none match filters.

        Example:
            >>> with ProjectRepository() as repo:
            ...     # Get last 5 commits
            ...     commits = repo.get_log(5)
            ...
            ...     # Get commits affecting a specific file
            ...     commits = repo.get_log(path=Path("src/main.py"))
            ...
            ...     # Search commit messages
            ...     commits = repo.get_log(grep="fix")
            ...
            ...     # Filter by author
            ...     commits = repo.get_log(author="alice")
        """
        head_sha = self._get_head_sha()
        if head_sha is None:
            return []

        head_bytes = bytes.fromhex(head_sha)

        # Calculate walker entries with overscan for filtered searches
        if grep is not None or author is not None:
            walker_max = n * _FILTER_OVERSCAN_MULTIPLIER
        else:
            walker_max = n

        walker = self._create_commit_walker(
            head_bytes, path=path, max_entries=walker_max
        )

        return self._apply_commit_filters(
            walker,
            grep=grep,
            author=author,
            max_results=n,
        )

    # =========================================================================
    # Blame Methods
    # =========================================================================

    def get_blame(
        self,
        path: Path,
        *,
        max_commits: int | None = 100,
    ) -> list[BlameLine]:
        """Get blame attribution for each line of a file.

        Args:
            path: Path to the file to blame (absolute or relative to repo root).
            max_commits: Reserved for future use. This parameter is accepted
                for API stability but currently has no effect. Git blame does
                not support direct commit depth limiting.

        Returns:
            List of BlameLine in line order. Returns empty list for empty files.

        Raises:
            FileNotFoundError: If file does not exist in working tree.
            OapsRepositoryPathViolationError: If path is within .oaps/ directory.

        Note:
            Uses native git blame for reliability. The max_commits parameter
            is reserved for future enhancement when git blame depth limiting
            becomes available or via alternative implementation.

        Example:
            >>> with ProjectRepository() as repo:
            ...     blame = repo.get_blame(repo.root / "src" / "main.py")
            ...     for line in blame[:5]:
            ...         print(f"{line.sha[:8]} {line.author_name}: {line.content}")
        """
        # Validate path
        resolved_path = self._validate_blame_path(path)

        # Convert to repo-relative path
        relative_path = str(resolved_path.relative_to(self._root))

        # Run git blame
        output = self._run_git_blame(relative_path, max_commits)
        if not output:
            return []

        # Parse and return
        return self._parse_blame_porcelain(output)

    def _validate_blame_path(self, path: Path) -> Path:
        """Validate and resolve path for blame operation.

        Args:
            path: Path to validate.

        Returns:
            Resolved absolute path.

        Raises:
            OapsRepositoryPathViolationError: If path is outside scope or in .oaps/.
            FileNotFoundError: If file does not exist.
        """
        # Resolve to absolute
        if path.is_absolute():
            resolved = path.resolve()
        else:
            resolved = (self._root / path).resolve()

        # Check path is in scope (not in .oaps/)
        if not self.validate_path(resolved):
            msg = f"Path is outside repository scope or in .oaps/: {path}"
            raise OapsRepositoryPathViolationError(msg, path=path, oaps_root=self._root)

        # Check file exists
        if not resolved.exists():
            msg = f"File not found: {path}"
            raise FileNotFoundError(msg)

        if not resolved.is_file():
            msg = f"Not a file: {path}"
            raise FileNotFoundError(msg)

        return resolved

    def _run_git_blame(
        self,
        relative_path: str,
        max_commits: int | None,
    ) -> str:
        """Execute git blame and return raw porcelain output.

        Args:
            relative_path: Repository-relative path string.
            max_commits: Maximum commits to traverse, or None for unlimited.

        Returns:
            Raw porcelain output from git blame. Empty string if file is empty
            or untracked.
        """
        # Note: max_commits is kept for API consistency and future enhancement.
        # git blame doesn't have a direct --max-commits flag, so it's not used.
        _ = max_commits

        cmd = ["git", "blame", "--porcelain", "--", relative_path]

        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(self._root),
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # File might be untracked or empty
            return ""

        return result.stdout

    def _parse_blame_porcelain(self, output: str) -> list[BlameLine]:
        """Parse git blame --porcelain output.

        The porcelain format is::

            <sha> <orig_line> <final_line> [<num_lines>]
            author <name>
            author-mail <<email>>
            author-time <timestamp>
            author-tz <tz>
            ... other headers ...
            filename <path>
                <content>

        Args:
            output: Raw porcelain output from git blame.

        Returns:
            List of BlameLine objects in file order.
        """
        lines = output.split("\n")
        result: list[BlameLine] = []

        # Cache for commit info to avoid re-parsing repeated SHAs
        commit_cache: dict[str, dict[str, str | int]] = {}

        i = 0
        while i < len(lines):
            line = lines[i]
            if not line:
                i += 1
                continue

            # Check if this is a commit header line (starts with hex SHA)
            if not self._is_blame_header_line(line):
                i += 1
                continue

            parts = line.split()
            sha = parts[0]
            final_line_no = (
                int(parts[2]) if len(parts) >= _MIN_BLAME_HEADER_PARTS else 1
            )

            # Parse or skip commit metadata based on cache
            i, commit_cache = self._process_commit_metadata(lines, i, sha, commit_cache)

            # Parse content line (starts with tab)
            if i < len(lines) and lines[i].startswith("\t"):
                blame_line = self._create_blame_line(
                    lines[i], sha, final_line_no, commit_cache
                )
                result.append(blame_line)

            i += 1

        return result

    def _is_blame_header_line(self, line: str) -> bool:
        """Check if a line is a blame commit header (starts with 40-char hex SHA).

        Args:
            line: Line to check.

        Returns:
            True if line starts with a valid SHA.
        """
        return len(line) >= _SHA_HEX_LENGTH and all(
            c in "0123456789abcdef" for c in line[:_SHA_HEX_LENGTH]
        )

    def _process_commit_metadata(
        self,
        lines: list[str],
        i: int,
        sha: str,
        commit_cache: dict[str, dict[str, str | int]],
    ) -> tuple[int, dict[str, dict[str, str | int]]]:
        """Parse or skip commit metadata lines based on cache state.

        Args:
            lines: All lines from blame output.
            i: Current line index (at header line).
            sha: Commit SHA from header.
            commit_cache: Cache of previously parsed commit info.

        Returns:
            Tuple of (new index at content line, updated cache).
        """
        if sha not in commit_cache:
            # Parse commit metadata from subsequent lines
            commit_info: dict[str, str | int] = {}
            i += 1
            while i < len(lines) and not lines[i].startswith("\t"):
                self._extract_commit_header(lines[i], commit_info)
                i += 1
            commit_cache[sha] = commit_info
        else:
            # Skip to content line for repeated SHA
            i += 1
            while i < len(lines) and not lines[i].startswith("\t"):
                i += 1

        return i, commit_cache

    def _extract_commit_header(
        self,
        header_line: str,
        commit_info: dict[str, str | int],
    ) -> None:
        """Extract author information from a single blame header line.

        Args:
            header_line: A header line from blame output.
            commit_info: Dictionary to update with extracted info.
        """
        if header_line.startswith("author "):
            commit_info["author_name"] = header_line[7:]
        elif header_line.startswith("author-mail "):
            # Strip angle brackets: <email> -> email
            email = header_line[12:].strip()
            if email.startswith("<") and email.endswith(">"):
                email = email[1:-1]
            commit_info["author_email"] = email
        elif header_line.startswith("author-time "):
            commit_info["author_time"] = int(header_line[12:])
        elif header_line.startswith("author-tz "):
            commit_info["author_tz"] = header_line[10:]

    def _create_blame_line(
        self,
        content_line: str,
        sha: str,
        final_line_no: int,
        commit_cache: dict[str, dict[str, str | int]],
    ) -> BlameLine:
        """Create a BlameLine from parsed content and cached commit info.

        Args:
            content_line: Line starting with tab containing file content.
            sha: Commit SHA for this line.
            final_line_no: 1-based line number in the file.
            commit_cache: Cache containing commit metadata.

        Returns:
            BlameLine with all attributes populated.
        """
        content = content_line[1:]  # Remove leading tab

        # Get cached commit info
        info = commit_cache[sha]
        author_name = str(info.get("author_name", ""))
        author_email = str(info.get("author_email", ""))
        author_time = int(info.get("author_time", 0))
        author_tz_str = str(info.get("author_tz", "+0000"))

        # Convert timestamp to datetime
        timestamp = self._parse_blame_timestamp(author_time, author_tz_str)

        return BlameLine(
            line_no=final_line_no,
            content=content,
            sha=sha,
            author_name=author_name,
            author_email=author_email,
            timestamp=timestamp,
        )

    def _parse_blame_timestamp(self, author_time: int, author_tz_str: str) -> datetime:
        """Convert blame timestamp and timezone to datetime.

        Args:
            author_time: Unix timestamp.
            author_tz_str: Timezone string like "+0100" or "-0500".

        Returns:
            Timezone-aware datetime.
        """
        # Parse timezone string to seconds offset
        # Format: +HHMM or -HHMM
        tz: timezone
        if not author_tz_str or len(author_tz_str) != _TZ_STRING_LENGTH:
            # Default to UTC
            tz = timezone.utc  # noqa: UP017
        else:
            sign = -1 if author_tz_str[0] == "-" else 1
            try:
                hours = int(author_tz_str[1:3])
                minutes = int(author_tz_str[3:5])
                offset_seconds = sign * (hours * 3600 + minutes * 60)
                tz = timezone(timedelta(seconds=offset_seconds))
            except ValueError:
                tz = timezone.utc  # noqa: UP017

        return datetime.fromtimestamp(author_time, tz=tz)

    # =========================================================================
    # Search and File History Methods
    # =========================================================================

    def _resolve_abbreviated_sha(self, sha: str) -> bytes:
        """Resolve abbreviated SHA to full SHA bytes.

        Resolves short commit references (minimum 4 characters) to their full
        40-character SHA. Full SHAs pass through unchanged.

        Args:
            sha: Commit SHA as hex string (4-40 characters).

        Returns:
            Full SHA as bytes (20 bytes).

        Raises:
            KeyError: If SHA is not found, is ambiguous, or is too short.
        """
        if len(sha) < _MIN_SHA_ABBREV_LENGTH:
            msg = f"SHA too short (minimum {_MIN_SHA_ABBREV_LENGTH} characters): {sha}"
            raise KeyError(msg)

        if len(sha) == _SHA_HEX_LENGTH:
            # Full SHA - convert directly
            try:
                return bytes.fromhex(sha)
            except ValueError as e:
                msg = f"Invalid SHA format: {sha}"
                raise KeyError(msg) from e

        # Abbreviated SHA - search for matches
        sha_lower = sha.lower()
        matches: list[bytes] = []

        for obj_sha in self._repo.object_store:
            sha_hex = obj_sha.hex()
            if sha_hex.startswith(sha_lower):
                # Verify it's a commit
                try:
                    obj = self._repo[obj_sha]
                    if hasattr(obj, "tree") and hasattr(obj, "parents"):
                        matches.append(obj_sha)
                except KeyError:
                    continue

        if not matches:
            msg = f"Commit not found: {sha}"
            raise KeyError(msg)

        if len(matches) > 1:
            msg = f"Ambiguous SHA prefix: {sha} (matches {len(matches)} commits)"
            raise KeyError(msg)

        return matches[0]

    def _create_commit_walker(
        self,
        head_bytes: bytes,
        *,
        path: Path | None = None,
        max_entries: int,
    ) -> Iterable[object]:
        """Create configured dulwich walker for commit traversal.

        Args:
            head_bytes: Starting commit SHA as bytes.
            path: Optional path filter for commits affecting this path.
            max_entries: Maximum number of entries to walk.

        Returns:
            Dulwich Walker object (iterable of WalkEntry), or empty iterator
            if path is outside repository.
        """
        walker_kwargs: dict[str, object] = {
            "include": [head_bytes],
            "max_entries": max_entries,
        }

        if path is not None:
            if path.is_absolute():
                if not path.is_relative_to(self._root):
                    # Path outside repo - return empty iterator (early optimization)
                    return iter([])
                relative_path = path.relative_to(self._root)
                walker_kwargs["paths"] = [str(relative_path).encode()]
            else:
                walker_kwargs["paths"] = [str(path).encode()]

        return self._repo.get_walker(**walker_kwargs)  # pyright: ignore[reportArgumentType]

    def _apply_commit_filters(
        self,
        walker: Iterable[object],
        *,
        grep: str | None = None,
        author: str | None = None,
        max_results: int,
    ) -> list[CommitInfo]:
        """Apply grep/author filters to walker and yield CommitInfo objects.

        Args:
            walker: Dulwich walker object (iterable of WalkEntry).
            grep: Case-insensitive substring to search for in commit messages.
            author: Case-insensitive substring to match against author name or email.
            max_results: Maximum number of results to return.

        Returns:
            List of CommitInfo matching the filters.
        """
        grep_lower = grep.lower() if grep else None
        author_lower = author.lower() if author else None

        commits: list[CommitInfo] = []
        for entry in walker:
            if len(commits) >= max_results:
                break

            commit: object = getattr(entry, "commit", None)
            if commit is None:
                continue

            # Extract commit attributes with explicit casts (dulwich stubs incomplete)
            author_bytes = cast("bytes", getattr(commit, "author", b""))
            author_time_val = cast("int", getattr(commit, "author_time", 0))
            author_tz_val = cast("int", getattr(commit, "author_timezone", 0))
            message_bytes = cast("bytes", getattr(commit, "message", b""))
            commit_id = cast("bytes", getattr(commit, "id", b""))
            parent_list = cast("list[bytes]", getattr(commit, "parents", []))

            # Parse author
            author_name, author_email, timestamp = self._parse_author_line(
                author_bytes,
                author_time_val,
                author_tz_val,
            )

            # Get message
            message_str = message_bytes.decode("utf-8", errors="replace")

            # Apply grep filter (case-insensitive message substring)
            if grep_lower is not None and grep_lower not in message_str.lower():
                continue

            # Apply author filter (case-insensitive name OR email match)
            if author_lower is not None and (
                author_lower not in author_name.lower()
                and author_lower not in author_email.lower()
            ):
                continue

            # Count files changed
            files_changed = self._count_files_changed(commit_id)

            # Get parent SHAs
            parent_shas = tuple(p.hex() for p in parent_list)

            commits.append(
                CommitInfo(
                    sha=commit_id.hex(),
                    message=message_str,
                    author_name=author_name,
                    author_email=author_email,
                    timestamp=timestamp,
                    files_changed=files_changed,
                    parent_shas=parent_shas,
                )
            )

        return commits

    def search_commits(
        self,
        *,
        grep: str | None = None,
        author: str | None = None,
        max_entries: int = _DEFAULT_SEARCH_MAX_ENTRIES,
        use_git_cli: bool = False,
    ) -> list[CommitInfo]:
        """Search commit history with optional filters.

        Searches the commit history starting from HEAD with support for
        filtering by message content and author. Unlike get_log(), this method
        is optimized for searching larger history with higher default limits.

        When no filters are provided, returns all commits up to max_entries.

        Args:
            grep: Case-insensitive substring to search for in commit messages.
            author: Case-insensitive substring to match against author name or email.
            max_entries: Maximum number of commits to return. Defaults to 1000.
            use_git_cli: Reserved for future use. If True, would use native git
                instead of dulwich for potentially better performance on large
                repositories. Currently has no effect.

        Returns:
            List of CommitInfo in reverse chronological order (newest first).
            Returns an empty list if no commits exist or none match filters.

        Example:
            >>> with ProjectRepository() as repo:
            ...     # Search for all bug fixes
            ...     fixes = repo.search_commits(grep="fix")
            ...
            ...     # Find commits by a specific author
            ...     alice_commits = repo.search_commits(author="alice@example.com")
            ...
            ...     # Get all commits (up to limit)
            ...     all_commits = repo.search_commits()
        """
        # Reserved parameter for future native git implementation
        _ = use_git_cli

        head_sha = self._get_head_sha()
        if head_sha is None:
            return []

        head_bytes = bytes.fromhex(head_sha)

        # Calculate walker entries with overscan for filtered searches
        if grep is not None or author is not None:
            walker_max = max_entries * _FILTER_OVERSCAN_MULTIPLIER
        else:
            walker_max = max_entries

        walker = self._create_commit_walker(head_bytes, max_entries=walker_max)

        return self._apply_commit_filters(
            walker,
            grep=grep,
            author=author,
            max_results=max_entries,
        )

    def get_file_at_commit(
        self,
        path: Path,
        commit: str,
    ) -> bytes | None:
        """Get file contents at a specific commit.

        Retrieves the contents of a file as it existed at a given commit.
        Useful for examining historical versions or comparing changes over time.

        Args:
            path: Path to the file (absolute or relative to repo root).
                Must not be within the .oaps/ directory.
            commit: Commit SHA (full 40-character or abbreviated minimum 4 chars).

        Returns:
            File contents as bytes, or None if the file does not exist
            at the specified commit.

        Raises:
            OapsRepositoryPathViolationError: If path is within .oaps/ directory.
            KeyError: If commit SHA is not found, ambiguous, or too short.

        Example:
            >>> with ProjectRepository() as repo:
            ...     # Get file at a specific commit
            ...     content = repo.get_file_at_commit(
            ...         Path("src/main.py"),
            ...         "abc1234",
            ...     )
            ...     if content:
            ...         print(content.decode("utf-8"))
            ...
            ...     # Using full SHA
            ...     content = repo.get_file_at_commit(
            ...         repo.root / "README.md",
            ...         "abc123def456789...",  # full 40 char SHA
            ...     )
        """
        # Resolve path to relative
        if path.is_absolute():
            resolved = path.resolve()
            if not resolved.is_relative_to(self._root):
                msg = f"Path is outside repository: {path}"
                raise OapsRepositoryPathViolationError(
                    msg, path=path, oaps_root=self._root
                )
            relative_path = str(resolved.relative_to(self._root))
        else:
            relative_path = str(path)
            resolved = (self._root / path).resolve()

        # Check for .oaps/ path violation
        if self._is_oaps_path(relative_path):
            msg = f"Cannot access files in {self._oaps_dir_name}/: {path}"
            raise OapsRepositoryPathViolationError(msg, path=path, oaps_root=self._root)

        # Resolve abbreviated SHA to full SHA bytes
        commit_bytes = self._resolve_abbreviated_sha(commit)

        # Get commit object and its tree
        commit_obj = self._repo[commit_bytes]
        tree_sha: bytes = getattr(commit_obj, "tree", b"")

        if not tree_sha:
            return None

        # Look up file in tree
        path_bytes = relative_path.encode("utf-8")
        try:
            _, blob_sha = tree_lookup_path(self._repo.__getitem__, tree_sha, path_bytes)
        except KeyError:
            # File does not exist at this commit
            return None

        # Get blob content
        blob = self._repo[blob_sha]
        content: bytes = getattr(blob, "data", b"")
        return content
