# ruff: noqa: TC003  # Path needed at runtime for method bodies
"""OAPS repository management.

This module provides the OapsRepository class for managing the .oaps/ git repository.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Final, override

if TYPE_CHECKING:
    from collections.abc import Iterable

from oaps.exceptions import OapsRepositoryNotInitializedError
from oaps.repository._base import BaseRepository
from oaps.repository._models import CommitResult, OapsRepoStatus

# Default identity when git config is not available
_DEFAULT_NAME: Final = "OAPS"
_DEFAULT_EMAIL: Final = "oaps@localhost"


class OapsRepository(BaseRepository[OapsRepoStatus]):
    """Manages the OAPS repository located at .oaps/ within a project.

    This class provides access to the git repository that stores OAPS
    configuration, artifacts, and metadata. It enforces path containment
    to ensure operations are confined to the .oaps/ directory.

    The class implements the context manager protocol for proper resource cleanup.
    When used as a context manager, the underlying dulwich Repo is automatically
    closed when exiting the context.

    Attributes:
        root: The resolved path to the .oaps/ directory.

    Example:
        with OapsRepository() as repo:
            status = repo.get_status()
            print(f"Staged files: {status.staged}")
    """

    # =========================================================================
    # Abstract Method Implementations (Template Method hooks)
    # =========================================================================

    @override
    def _discover_root(self, working_dir: Path) -> Path:
        """Discover .oaps/ directory within project.

        Args:
            working_dir: The project working directory containing .oaps/.

        Returns:
            The resolved path to the .oaps/ directory.

        Raises:
            OapsRepositoryNotInitializedError: If .oaps/.git is not found.
        """
        oaps_path = working_dir / ".oaps"
        resolved_path = oaps_path.resolve()

        # Check if .oaps/.git exists (dulwich handles gitdir pointer files)
        git_path = resolved_path / ".git"
        if not git_path.exists():
            msg = f"OAPS repository not initialized: {resolved_path}/.git not found"
            raise OapsRepositoryNotInitializedError(msg, path=resolved_path)

        return resolved_path

    @override
    def validate_path(self, path: Path) -> bool:
        """Validate that a path is within the OAPS repository.

        Args:
            path: The path to validate.

        Returns:
            True if the resolved path is within the OAPS repository root.
        """
        resolved = path.resolve()
        return resolved.is_relative_to(self._root)

    @override
    def _create_status(
        self,
        staged: frozenset[Path],
        modified: frozenset[Path],
        untracked: frozenset[Path],
    ) -> OapsRepoStatus:
        """Create OapsRepoStatus instance.

        Args:
            staged: Files that are staged for commit.
            modified: Files that are modified but not staged.
            untracked: Files that are not tracked by git.

        Returns:
            OapsRepoStatus with the given file sets.
        """
        return OapsRepoStatus(staged=staged, modified=modified, untracked=untracked)

    # =========================================================================
    # OAPS-Specific Private Helper Methods
    # =========================================================================

    def _format_oaps_coauthor(self) -> str:
        """Format the OAPS co-author trailer.

        Returns:
            Co-authored-by trailer line.
        """
        return f"Co-authored-by: {_DEFAULT_NAME} <{_DEFAULT_EMAIL}>"

    def _format_session_trailer(self, session_id: str) -> str:
        """Format the session ID trailer.

        Args:
            session_id: The session identifier to include.

        Returns:
            OAPS-Session trailer line.
        """
        return f"OAPS-Session: {session_id}"

    def _build_commit_message(self, subject: str, *, session_id: str | None) -> bytes:
        """Compose commit message with trailers.

        The message format includes:
        - Subject line
        - Blank line
        - Co-authored-by trailer
        - Session trailer (if session_id provided)

        Args:
            subject: The commit subject line.
            session_id: Optional session identifier for trailer.

        Returns:
            Complete commit message as bytes.
        """
        lines = [subject, "", self._format_oaps_coauthor()]
        if session_id is not None:
            lines.append(self._format_session_trailer(session_id))
        return "\n".join(lines).encode()

    def _format_checkpoint_subject(self, workflow: str, action: str) -> str:
        """Format a checkpoint commit subject line.

        Args:
            workflow: The workflow name (e.g., "spec", "idea").
            action: The action being checkpointed.

        Returns:
            Formatted subject line "oaps(<workflow>): <action>".
        """
        return f"oaps({workflow}): {action}"

    # =========================================================================
    # OAPS-Specific Public Commit Methods
    # =========================================================================

    def commit_pending(
        self, message: str, *, session_id: str | None = None
    ) -> CommitResult:
        """Commit all pending changes in the repository.

        Stages and commits all modified and untracked files. The commit
        includes a Co-authored-by trailer for OAPS and optionally a session
        ID trailer for traceability.

        Args:
            message: Commit message subject line.
            session_id: Optional session identifier included as a trailer
                in the format "OAPS-Session: <session_id>".

        Returns:
            CommitResult containing:
                - sha: The commit SHA hex string, or None if no changes
                - files: Frozenset of committed file paths
                - no_changes: True if nothing was committed

        Raises:
            OapsRepositoryConflictError: If another process committed changes
                between staging and committing (race condition detected).

        Example:
            >>> with OapsRepository() as repo:
            ...     result = repo.commit_pending(
            ...         "Add new specification", session_id="abc-123"
            ...     )
            ...     if result.no_changes:
            ...         print("Nothing to commit")
            ...     else:
            ...         print(f"Committed {len(result.files)} files: {result.sha}")
        """
        # Stage all pending changes
        staged_files = self._stage_pending()
        if not staged_files:
            return CommitResult(sha=None, files=frozenset(), no_changes=True)

        # Build commit message and perform commit
        commit_message = self._build_commit_message(message, session_id=session_id)
        return self._perform_commit(commit_message, staged_files)

    def commit_files(
        self,
        paths: Iterable[Path],
        message: str,
        *,
        session_id: str | None = None,
    ) -> CommitResult:
        """Commit specific files from the repository.

        Stages and commits only the specified files, leaving other uncommitted
        changes intact. All paths must be within the .oaps/ directory.

        Args:
            paths: Absolute paths to the files to commit. Each path is validated
                to ensure it is within the OAPS repository root.
            message: Commit message subject line.
            session_id: Optional session identifier included as a trailer
                in the format "OAPS-Session: <session_id>".

        Returns:
            CommitResult containing:
                - sha: The commit SHA hex string, or None if no changes
                - files: Frozenset of committed file paths
                - no_changes: True if nothing was committed

        Raises:
            OapsRepositoryPathViolationError: If any path resolves outside
                the .oaps/ directory (including via symlinks).
            OapsRepositoryConflictError: If another process committed changes
                between staging and committing (race condition detected).

        Example:
            >>> with OapsRepository() as repo:
            ...     spec_file = repo.root / "docs" / "specs" / "SPEC-0001.md"
            ...     result = repo.commit_files(
            ...         [spec_file], "Update specification SPEC-0001"
            ...     )
            ...     print(f"Committed: {result.sha[:8]}")
        """
        # Stage the specified files
        staged_files = self.stage(paths)
        if not staged_files:
            return CommitResult(sha=None, files=frozenset(), no_changes=True)

        # Build commit message and perform commit
        commit_message = self._build_commit_message(message, session_id=session_id)
        return self._perform_commit(commit_message, staged_files)

    def checkpoint(
        self, workflow: str, action: str, *, session_id: str | None = None
    ) -> CommitResult:
        """Create a checkpoint commit for workflow state.

        Commits all pending changes with a standardized checkpoint message
        following the conventional commit format "oaps(<workflow>): <action>".
        This is the preferred method for automated workflow commits.

        Args:
            workflow: The workflow name used as the scope (e.g., "spec", "idea",
                "session"). Forms the "oaps(<workflow>)" part of the message.
            action: Description of the action being checkpointed. Forms the
                subject line after the colon (e.g., "create SPEC-0001").
            session_id: Optional session identifier included as a trailer
                in the format "OAPS-Session: <session_id>".

        Returns:
            CommitResult containing:
                - sha: The commit SHA hex string, or None if no changes
                - files: Frozenset of committed file paths
                - no_changes: True if nothing was committed

        Raises:
            OapsRepositoryConflictError: If another process committed changes
                between staging and committing (race condition detected).

        Example:
            >>> with OapsRepository() as repo:
            ...     # Commit after creating a new spec
            ...     result = repo.checkpoint(
            ...         workflow="spec",
            ...         action="create SPEC-0001",
            ...         session_id="session-xyz",
            ...     )
            ...     # Message: "oaps(spec): create SPEC-0001"
            ...     print(f"Checkpoint created: {result.sha[:8]}")
        """
        subject = self._format_checkpoint_subject(workflow, action)
        return self.commit_pending(subject, session_id=session_id)
