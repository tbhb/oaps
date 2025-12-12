"""Unit tests for Phase 4 Feedback Actions (LogAction, SuggestAction, InjectAction)."""

from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import pytest

from oaps.config import HookRuleActionConfiguration
from oaps.enums import HookEventType
from oaps.hooks._action import (
    InjectAction,
    LogAction,
    OutputAccumulator,
    SuggestAction,
)
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import (
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionStartInput,
    StopInput,
    UserPromptSubmitInput,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def mock_logger() -> MagicMock:
    from unittest.mock import MagicMock

    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def pre_tool_use_input(tmp_path: Path) -> PreToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PreToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd="/home/user/project",
        tool_name="Bash",
        tool_input={"command": "ls -la"},
        tool_use_id="tool-123",
    )


@pytest.fixture
def pre_tool_use_context(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def session_start_input(tmp_path: Path) -> SessionStartInput:
    transcript = tmp_path / "transcript.json"
    return SessionStartInput(
        session_id=UUID("12345678-1234-5678-1234-567812345678"),
        transcript_path=transcript,
        hook_event_name="SessionStart",
        cwd=Path("/home/user/project"),
        source="startup",
    )


@pytest.fixture
def session_start_context(
    session_start_input: SessionStartInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.SESSION_START,
        hook_input=session_start_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def post_tool_use_input(tmp_path: Path) -> PostToolUseInput:
    transcript = tmp_path / "transcript.json"
    return PostToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PostToolUse",
        cwd="/home/user/project",
        tool_name="Bash",
        tool_input={"command": "ls -la"},
        tool_use_id="tool-123",
        tool_response={"content": "file1.txt\nfile2.txt"},
    )


@pytest.fixture
def post_tool_use_context(
    post_tool_use_input: PostToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.POST_TOOL_USE,
        hook_input=post_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def pre_compact_input(tmp_path: Path) -> PreCompactInput:
    transcript = tmp_path / "transcript.json"
    return PreCompactInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreCompact",
        cwd="/home/user/project",
        trigger="manual",
        custom_instructions="Test custom instructions",
    )


@pytest.fixture
def pre_compact_context(
    pre_compact_input: PreCompactInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PRE_COMPACTION,
        hook_input=pre_compact_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def user_prompt_submit_input(tmp_path: Path) -> UserPromptSubmitInput:
    transcript = tmp_path / "transcript.json"
    return UserPromptSubmitInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="UserPromptSubmit",
        cwd="/home/user/project",
        prompt="Please run ls -la",
    )


@pytest.fixture
def user_prompt_submit_context(
    user_prompt_submit_input: UserPromptSubmitInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.USER_PROMPT_SUBMIT,
        hook_input=user_prompt_submit_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def stop_input(tmp_path: Path) -> StopInput:
    transcript = tmp_path / "transcript.json"
    return StopInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="Stop",
        cwd="/home/user/project",
        stop_hook_active=False,
    )


@pytest.fixture
def stop_context(
    stop_input: StopInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.STOP,
        hook_input=stop_input,
        claude_session_id="test-session",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


@pytest.fixture
def output_accumulator() -> OutputAccumulator:
    return OutputAccumulator()


def make_action_config(
    action_type: str = "log",
    *,
    message: str | None = None,
    level: str | None = None,
    content: str | None = None,
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(
        type=action_type,  # pyright: ignore[reportArgumentType]
        message=message,
        level=level,  # pyright: ignore[reportArgumentType]
        content=content,
    )


class TestLogAction:
    def test_logs_at_debug_level(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Debug message", level="debug")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.debug.assert_called_once_with("Debug message")

    def test_logs_at_info_level(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Info message", level="info")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.info.assert_called_once_with("Info message")

    def test_logs_at_warning_level(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Warning message", level="warning")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once_with("Warning message")

    def test_logs_at_error_level(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Error message", level="error")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.error.assert_called_once_with("Error message")

    def test_defaults_to_info_when_level_not_specified(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Default level message")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.info.assert_called_once_with("Default level message")

    def test_message_template_substitution(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config(
            "log", message="Tool ${tool_name} used in ${cwd}", level="info"
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.info.assert_called_once_with("Tool Bash used in /home/user/project")

    def test_template_substitution_with_nested_tool_input(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config(
            "log", message="Command: ${tool_input.command}", level="info"
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.info.assert_called_once_with("Command: ls -la")

    def test_empty_message_does_not_log(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message=None, level="info")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.debug.assert_not_called()
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    def test_empty_string_message_does_not_log(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="", level="info")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.info.assert_not_called()

    def test_does_not_modify_accumulator(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Log message", level="info")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None
        assert len(output_accumulator.system_messages) == 0
        assert len(output_accumulator.additional_context_items) == 0

    def test_does_not_block_execution(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = LogAction()
        config = make_action_config("log", message="Log message", level="error")

        # Should complete without raising any exception
        result = action.run(pre_tool_use_context, config, output_accumulator)

        assert result is None


class TestSuggestAction:
    def test_adds_message_to_additional_context_for_supported_hooks(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Consider using --verbose flag")

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        items = output_accumulator.additional_context_items
        assert "Consider using --verbose flag" in items

    def test_message_template_substitution(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Consider: ${prompt} in ${cwd}")

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Consider: Please run ls -la in /home/user/project"
        assert output_accumulator.additional_context_items[0] == expected

    def test_does_not_block_execution(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Just a suggestion")

        result = action.run(user_prompt_submit_context, config, output_accumulator)

        assert result is None

    def test_does_not_set_permission_decision(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Suggestion message")

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None

    def test_empty_message_does_not_add_to_context(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message=None)

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 0

    def test_empty_string_message_does_not_add_to_context(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="")

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 0

    def test_multiple_suggestions_accumulate(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()

        config1 = make_action_config("suggest", message="First suggestion")
        action.run(user_prompt_submit_context, config1, output_accumulator)

        config2 = make_action_config("suggest", message="Second suggestion")
        action.run(user_prompt_submit_context, config2, output_accumulator)

        config3 = make_action_config("suggest", message="Third suggestion")
        action.run(user_prompt_submit_context, config3, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 3
        assert output_accumulator.additional_context_items[0] == "First suggestion"
        assert output_accumulator.additional_context_items[1] == "Second suggestion"
        assert output_accumulator.additional_context_items[2] == "Third suggestion"

    def test_logs_warning_for_unsupported_hook_types(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="This won't be injected")

        action.run(pre_tool_use_context, config, output_accumulator)

        # Should not add to context for unsupported hook types
        assert len(output_accumulator.additional_context_items) == 0
        assert len(output_accumulator.system_messages) == 0
        # Should log a warning
        mock_logger.warning.assert_called_once()

    def test_works_with_session_start_hook(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Session suggestion")

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert "Session suggestion" in output_accumulator.additional_context_items

    def test_works_with_post_tool_use_hook(
        self,
        post_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Post tool suggestion")

        action.run(post_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert "Post tool suggestion" in output_accumulator.additional_context_items

    def test_works_with_pre_compact_hook(
        self,
        pre_compact_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = SuggestAction()
        config = make_action_config("suggest", message="Pre compact suggestion")

        action.run(pre_compact_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert "Pre compact suggestion" in output_accumulator.additional_context_items


class TestInjectAction:
    def test_injects_content_for_session_start(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config(
            "inject", content="Session context: Welcome to the project"
        )

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Session context: Welcome to the project"
        assert output_accumulator.additional_context_items[0] == expected

    def test_injects_content_for_post_tool_use(
        self,
        post_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Tool completed successfully")

        action.run(post_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert (
            output_accumulator.additional_context_items[0]
            == "Tool completed successfully"
        )

    def test_injects_content_for_pre_compact(
        self,
        pre_compact_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config(
            "inject", content="Remember: important project context"
        )

        action.run(pre_compact_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Remember: important project context"
        assert output_accumulator.additional_context_items[0] == expected

    def test_injects_content_for_user_prompt_submit(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config(
            "inject", content="Additional context for the prompt"
        )

        action.run(user_prompt_submit_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Additional context for the prompt"
        assert output_accumulator.additional_context_items[0] == expected

    def test_logs_warning_for_unsupported_hook_type(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Should not be injected")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "unsupported hook type" in str(call_args)

    def test_does_not_inject_for_unsupported_hook_type(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Should not be injected")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 0

    def test_logs_warning_for_stop_hook_type(
        self,
        stop_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Should not be injected")

        action.run(stop_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert len(output_accumulator.additional_context_items) == 0

    def test_content_template_substitution(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Working directory: ${cwd}")

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Working directory: /home/user/project"
        assert output_accumulator.additional_context_items[0] == expected

    def test_fallback_to_message_field(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        # Use message instead of content
        config = make_action_config("inject", message="Fallback content")

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert output_accumulator.additional_context_items[0] == "Fallback content"

    def test_content_takes_precedence_over_message(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = HookRuleActionConfiguration(
            type="inject",
            content="Content field",
            message="Message field",
        )

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert output_accumulator.additional_context_items[0] == "Content field"

    def test_empty_content_does_not_inject(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content=None)

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 0

    def test_empty_string_content_does_not_inject(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="")

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 0

    def test_multiple_injections_accumulate(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()

        config1 = make_action_config("inject", content="First context")
        action.run(session_start_context, config1, output_accumulator)

        config2 = make_action_config("inject", content="Second context")
        action.run(session_start_context, config2, output_accumulator)

        config3 = make_action_config("inject", content="Third context")
        action.run(session_start_context, config3, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 3
        assert output_accumulator.additional_context_items[0] == "First context"
        assert output_accumulator.additional_context_items[1] == "Second context"
        assert output_accumulator.additional_context_items[2] == "Third context"

    def test_does_not_block_execution(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Context content")

        result = action.run(session_start_context, config, output_accumulator)

        assert result is None

    def test_does_not_affect_permission_decisions(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Context content")

        action.run(session_start_context, config, output_accumulator)

        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None

    def test_does_not_affect_system_messages(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = InjectAction()
        config = make_action_config("inject", content="Context content")

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 0


class TestOutputAccumulatorContextExtensions:
    def test_add_context_appends_to_list(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_context("First context")

        assert len(accumulator.additional_context_items) == 1
        assert accumulator.additional_context_items[0] == "First context"

    def test_add_context_multiple_times_preserves_order(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_context("Context 1")
        accumulator.add_context("Context 2")
        accumulator.add_context("Context 3")

        assert len(accumulator.additional_context_items) == 3
        assert accumulator.additional_context_items == [
            "Context 1",
            "Context 2",
            "Context 3",
        ]

    def test_add_context_does_not_affect_permission_decisions(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_context("Some context")

        assert accumulator.permission_decision is None
        assert accumulator.permission_request_decision is None

    def test_add_context_does_not_affect_system_messages(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_context("Some context")

        assert len(accumulator.system_messages) == 0

    def test_add_warning_does_not_affect_additional_context_items(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_warning("Some warning")

        assert len(accumulator.additional_context_items) == 0
