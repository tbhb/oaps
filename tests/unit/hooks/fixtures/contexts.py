"""HookContext factory for hook testing.

Provides a factory class that creates properly initialized HookContext instances
for each event type with sensible defaults.
"""

from pathlib import Path
from typing import final
from unittest.mock import MagicMock
from uuid import uuid4

from oaps.enums import HookEventType
from oaps.hooks import (
    NotificationInput,
    PermissionRequestInput,
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UserPromptSubmitInput,
)
from oaps.hooks._context import HookContext
from oaps.utils import GitContext

from .inputs import (
    NotificationInputBuilder,
    PermissionRequestInputBuilder,
    PostToolUseInputBuilder,
    PreCompactInputBuilder,
    PreToolUseInputBuilder,
    SessionEndInputBuilder,
    SessionStartInputBuilder,
    StopInputBuilder,
    SubagentStopInputBuilder,
    UserPromptSubmitInputBuilder,
)

# Type alias matching HookInputT from _inputs.py
type HookInputT = (
    PreToolUseInput
    | PostToolUseInput
    | UserPromptSubmitInput
    | PermissionRequestInput
    | NotificationInput
    | SessionStartInput
    | SessionEndInput
    | StopInput
    | SubagentStopInput
    | PreCompactInput
)


def create_mock_logger() -> MagicMock:
    """Create a mock logger with all expected methods."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def create_git_context(
    tmp_path: Path,
    *,
    branch: str | None = "main",
    is_dirty: bool = False,
    staged_files: frozenset[str] | None = None,
    modified_files: frozenset[str] | None = None,
    untracked_files: frozenset[str] | None = None,
) -> GitContext:
    """Create a GitContext with sensible defaults.

    Args:
        tmp_path: Base path for worktree directories.
        branch: Current branch name, None if detached.
        is_dirty: Whether the repo has uncommitted changes.
        staged_files: Set of staged file paths.
        modified_files: Set of modified file paths.
        untracked_files: Set of untracked file paths.

    Returns:
        GitContext configured with the given parameters.
    """
    return GitContext(
        main_worktree_dir=tmp_path,
        worktree_dir=tmp_path,
        head_commit="abc123def456",
        is_detached=branch is None,
        is_dirty=is_dirty,
        staged_files=staged_files or frozenset(),
        modified_files=modified_files or frozenset(),
        untracked_files=untracked_files or frozenset(),
        conflict_files=frozenset(),
        branch=branch,
        tag=None,
    )


@final
class HookContextFactory:
    """Factory for creating HookContext instances in tests.

    Takes a tmp_path at construction and creates properly initialized
    HookContext instances for each event type.
    """

    def __init__(self, tmp_path: Path) -> None:
        self._tmp_path: Path = tmp_path
        self._oaps_dir: Path = tmp_path / ".oaps"
        self._oaps_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir: Path = self._oaps_dir / "state"
        self._state_dir.mkdir(exist_ok=True)
        self._session_id: str = str(uuid4())
        self._mock_logger: MagicMock = create_mock_logger()

    @property
    def oaps_dir(self) -> Path:
        """The .oaps directory path."""
        return self._oaps_dir

    @property
    def session_id(self) -> str:
        """The session ID used for all contexts."""
        return self._session_id

    @property
    def mock_logger(self) -> MagicMock:
        """The mock logger used for all contexts."""
        return self._mock_logger

    def _create_context(
        self,
        event_type: HookEventType,
        hook_input: HookInputT,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a HookContext with standard setup.

        Args:
            event_type: The hook event type.
            hook_input: The hook input model.
            git: Optional GitContext.

        Returns:
            A fully configured HookContext.
        """
        return HookContext(
            hook_event_type=event_type,
            hook_input=hook_input,
            claude_session_id=self._session_id,
            oaps_dir=self._oaps_dir,
            oaps_state_file=self._state_dir / "state.db",
            hook_logger=self._mock_logger,
            session_logger=self._mock_logger,
            git=git,
        )

    def pre_tool_use(
        self,
        input_builder: PreToolUseInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a PreToolUse context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for PreToolUse event.
        """
        builder = input_builder or PreToolUseInputBuilder()
        return self._create_context(
            HookEventType.PRE_TOOL_USE,
            builder.build(),
            git,
        )

    def post_tool_use(
        self,
        input_builder: PostToolUseInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a PostToolUse context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for PostToolUse event.
        """
        builder = input_builder or PostToolUseInputBuilder()
        return self._create_context(
            HookEventType.POST_TOOL_USE,
            builder.build(),
            git,
        )

    def user_prompt_submit(
        self,
        prompt: str = "hello",
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a UserPromptSubmit context.

        Args:
            prompt: The user's prompt text.
            git: Optional GitContext.

        Returns:
            HookContext for UserPromptSubmit event.
        """
        builder = UserPromptSubmitInputBuilder().with_prompt(prompt)
        return self._create_context(
            HookEventType.USER_PROMPT_SUBMIT,
            builder.build(),
            git,
        )

    def permission_request(
        self,
        input_builder: PermissionRequestInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a PermissionRequest context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for PermissionRequest event.
        """
        builder = input_builder or PermissionRequestInputBuilder()
        return self._create_context(
            HookEventType.PERMISSION_REQUEST,
            builder.build(),
            git,
        )

    def notification(
        self,
        input_builder: NotificationInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a Notification context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for Notification event.
        """
        builder = input_builder or NotificationInputBuilder()
        return self._create_context(
            HookEventType.NOTIFICATION,
            builder.build(),
            git,
        )

    def session_start(
        self,
        input_builder: SessionStartInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a SessionStart context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for SessionStart event.
        """
        builder = input_builder or SessionStartInputBuilder()
        return self._create_context(
            HookEventType.SESSION_START,
            builder.build(),
            git,
        )

    def session_end(
        self,
        input_builder: SessionEndInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a SessionEnd context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for SessionEnd event.
        """
        builder = input_builder or SessionEndInputBuilder()
        return self._create_context(
            HookEventType.SESSION_END,
            builder.build(),
            git,
        )

    def stop(
        self,
        input_builder: StopInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a Stop context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for Stop event.
        """
        builder = input_builder or StopInputBuilder()
        return self._create_context(
            HookEventType.STOP,
            builder.build(),
            git,
        )

    def subagent_stop(
        self,
        input_builder: SubagentStopInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a SubagentStop context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for SubagentStop event.
        """
        builder = input_builder or SubagentStopInputBuilder()
        return self._create_context(
            HookEventType.SUBAGENT_STOP,
            builder.build(),
            git,
        )

    def pre_compact(
        self,
        input_builder: PreCompactInputBuilder | None = None,
        git: GitContext | None = None,
    ) -> HookContext:
        """Create a PreCompact context.

        Args:
            input_builder: Optional input builder. If None, uses defaults.
            git: Optional GitContext.

        Returns:
            HookContext for PreCompact event.
        """
        builder = input_builder or PreCompactInputBuilder()
        return self._create_context(
            HookEventType.PRE_COMPACTION,
            builder.build(),
            git,
        )
