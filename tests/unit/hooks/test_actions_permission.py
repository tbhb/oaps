"""Unit tests for Phase 3 Permission Actions (DenyAction, AllowAction, WarnAction)."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.config import HookRuleActionConfiguration
from oaps.enums import HookEventType
from oaps.exceptions import BlockHook
from oaps.hooks._action import (
    AllowAction,
    DenyAction,
    OutputAccumulator,
    WarnAction,
)
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import (
    PermissionRequestInput,
    PreToolUseInput,
    UserPromptSubmitInput,
)
from oaps.hooks._outputs import PermissionRequestDecision

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def mock_logger() -> MagicMock:
    from unittest.mock import MagicMock

    logger = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
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
def permission_request_input(tmp_path: Path) -> PermissionRequestInput:
    transcript = tmp_path / "transcript.json"
    return PermissionRequestInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PermissionRequest",
        cwd="/home/user/project",
        tool_name="Write",
        tool_input={"file_path": "/etc/passwd", "content": "malicious"},
        tool_use_id="tool-456",
    )


@pytest.fixture
def permission_request_context(
    permission_request_input: PermissionRequestInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    return HookContext(
        hook_event_type=HookEventType.PERMISSION_REQUEST,
        hook_input=permission_request_input,
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
        prompt="Please run rm -rf /",
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
def output_accumulator() -> OutputAccumulator:
    return OutputAccumulator()


def make_action_config(
    action_type: str = "deny",
    *,
    message: str | None = None,
    interrupt: bool = True,
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(
        type=action_type,  # pyright: ignore[reportArgumentType]
        message=message,
        interrupt=interrupt,
    )


class TestDenyAction:
    def test_pre_tool_use_sets_deny_and_raises_block_hook(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message="Operation denied")

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.permission_decision == "deny"
        assert output_accumulator.permission_decision_reason == "Operation denied"
        assert str(exc_info.value) == "Operation denied"

    def test_pre_tool_use_with_empty_message_uses_default(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message=None)

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.permission_decision == "deny"
        assert output_accumulator.permission_decision_reason is None
        assert str(exc_info.value) == "Operation denied by hook rule"

    def test_permission_request_sets_decision_and_raises_block_hook(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message="Permission denied", interrupt=True)

        with pytest.raises(BlockHook) as exc_info:
            action.run(permission_request_context, config, output_accumulator)

        assert output_accumulator.permission_request_decision is not None
        decision = output_accumulator.permission_request_decision
        assert decision.behavior == "deny"
        assert decision.message == "Permission denied"
        assert decision.interrupt is True
        assert str(exc_info.value) == "Permission denied"

    def test_permission_request_respects_interrupt_flag_false(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config(
            "deny", message="Permission denied", interrupt=False
        )

        with pytest.raises(BlockHook):
            action.run(permission_request_context, config, output_accumulator)

        decision = output_accumulator.permission_request_decision
        assert decision is not None
        assert decision.interrupt is False

    def test_permission_request_with_empty_message_uses_default(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message=None)

        with pytest.raises(BlockHook) as exc_info:
            action.run(permission_request_context, config, output_accumulator)

        decision = output_accumulator.permission_request_decision
        assert decision is not None
        assert decision.message is None
        assert str(exc_info.value) == "Permission request denied by hook rule"

    def test_user_prompt_submit_raises_block_hook_with_message(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message="Prompt blocked")

        with pytest.raises(BlockHook) as exc_info:
            action.run(user_prompt_submit_context, config, output_accumulator)

        # For non-permission contexts, should not set permission_decision
        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None
        assert str(exc_info.value) == "Prompt blocked"

    def test_user_prompt_submit_with_empty_message_uses_default(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message=None)

        with pytest.raises(BlockHook) as exc_info:
            action.run(user_prompt_submit_context, config, output_accumulator)

        assert str(exc_info.value) == "Operation blocked by hook rule"

    def test_message_template_substitution_tool_name(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message="Tool ${tool_name} is not allowed")

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert str(exc_info.value) == "Tool Bash is not allowed"

    def test_message_template_substitution_cwd(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config("deny", message="Cannot run in ${cwd}")

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert str(exc_info.value) == "Cannot run in /home/user/project"

    def test_message_template_substitution_nested_tool_input(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config(
            "deny", message="Command blocked: ${tool_input.command}"
        )

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert str(exc_info.value) == "Command blocked: ls -la"

    def test_message_template_substitution_multiple_variables(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = DenyAction()
        config = make_action_config(
            "deny",
            message="${tool_name} with '${tool_input.command}' in ${cwd} is blocked",
        )

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        expected = "Bash with 'ls -la' in /home/user/project is blocked"
        assert str(exc_info.value) == expected


class TestAllowAction:
    def test_pre_tool_use_sets_allow(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = AllowAction()
        config = make_action_config("allow")

        # Should NOT raise BlockHook
        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.permission_decision == "allow"

    def test_permission_request_sets_decision_with_allow(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = AllowAction()
        config = make_action_config("allow")

        action.run(permission_request_context, config, output_accumulator)

        assert output_accumulator.permission_request_decision is not None
        decision = output_accumulator.permission_request_decision
        assert decision.behavior == "allow"
        assert decision.message is None

    def test_user_prompt_submit_is_noop(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = AllowAction()
        config = make_action_config("allow")

        # Should NOT raise BlockHook and should leave accumulator unchanged
        action.run(user_prompt_submit_context, config, output_accumulator)

        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None

    def test_does_not_raise_block_hook(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = AllowAction()
        config = make_action_config("allow")

        # This should complete without raising any exception
        result = action.run(pre_tool_use_context, config, output_accumulator)

        # run() returns None, not a value indicating success
        assert result is None

    def test_allow_does_not_add_system_messages(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = AllowAction()
        config = make_action_config("allow", message="This should be ignored")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 0


class TestWarnAction:
    def test_adds_message_to_system_messages(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message="This is a warning")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 1
        assert "This is a warning" in output_accumulator.system_messages

    def test_message_template_substitution(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config(
            "warn", message="Warning: ${tool_name} used in ${cwd}"
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 1
        assert (
            output_accumulator.system_messages[0]
            == "Warning: Bash used in /home/user/project"
        )

    def test_does_not_raise_block_hook(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message="Just a warning")

        # Should complete without raising any exception
        result = action.run(pre_tool_use_context, config, output_accumulator)

        assert result is None

    def test_does_not_set_permission_decision(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message="Warning message")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.permission_decision is None
        assert output_accumulator.permission_request_decision is None

    def test_empty_message_does_not_add_to_system_messages(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message=None)

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 0

    def test_empty_string_message_does_not_add_to_system_messages(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message="")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 0

    def test_multiple_warnings_can_be_added(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()

        # Add first warning
        config1 = make_action_config("warn", message="First warning")
        action.run(pre_tool_use_context, config1, output_accumulator)

        # Add second warning
        config2 = make_action_config("warn", message="Second warning")
        action.run(pre_tool_use_context, config2, output_accumulator)

        # Add third warning
        config3 = make_action_config("warn", message="Third warning")
        action.run(pre_tool_use_context, config3, output_accumulator)

        assert len(output_accumulator.system_messages) == 3
        assert output_accumulator.system_messages[0] == "First warning"
        assert output_accumulator.system_messages[1] == "Second warning"
        assert output_accumulator.system_messages[2] == "Third warning"

    def test_works_with_permission_request_context(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = WarnAction()
        config = make_action_config("warn", message="Permission request warning")

        action.run(permission_request_context, config, output_accumulator)

        assert len(output_accumulator.system_messages) == 1
        assert output_accumulator.system_messages[0] == "Permission request warning"
        # Should not set permission_request_decision
        assert output_accumulator.permission_request_decision is None


class TestOutputAccumulator:
    def test_set_deny_sets_permission_decision_to_deny(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_deny()

        assert accumulator.permission_decision == "deny"

    def test_set_deny_with_reason_sets_both_fields(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_deny("Access denied for security reasons")

        assert accumulator.permission_decision == "deny"
        expected_reason = "Access denied for security reasons"
        assert accumulator.permission_decision_reason == expected_reason

    def test_set_deny_without_reason_leaves_reason_none(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_deny()

        assert accumulator.permission_decision == "deny"
        assert accumulator.permission_decision_reason is None

    def test_set_deny_with_empty_string_leaves_reason_none(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_deny("")

        assert accumulator.permission_decision == "deny"
        # Empty string is falsy, so reason should remain None
        assert accumulator.permission_decision_reason is None

    def test_set_allow_sets_permission_decision_to_allow(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_allow()

        assert accumulator.permission_decision == "allow"

    def test_set_allow_does_not_set_reason(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_allow()

        assert accumulator.permission_decision_reason is None

    def test_add_warning_appends_to_system_messages(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_warning("First warning")

        assert len(accumulator.system_messages) == 1
        assert accumulator.system_messages[0] == "First warning"

    def test_add_warning_multiple_times(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_warning("Warning 1")
        accumulator.add_warning("Warning 2")
        accumulator.add_warning("Warning 3")

        assert len(accumulator.system_messages) == 3
        assert accumulator.system_messages == ["Warning 1", "Warning 2", "Warning 3"]

    def test_add_warning_preserves_order(self) -> None:
        accumulator = OutputAccumulator()
        for i in range(10):
            accumulator.add_warning(f"Warning {i}")

        for i in range(10):
            assert accumulator.system_messages[i] == f"Warning {i}"

    def test_permission_request_decision_can_be_set_directly(self) -> None:
        accumulator = OutputAccumulator()
        decision = PermissionRequestDecision(
            behavior="deny",
            message="Direct denial",
            interrupt=True,
        )
        accumulator.permission_request_decision = decision

        assert accumulator.permission_request_decision is not None
        assert accumulator.permission_request_decision.behavior == "deny"
        assert accumulator.permission_request_decision.message == "Direct denial"
        assert accumulator.permission_request_decision.interrupt is True

    def test_set_deny_does_not_affect_permission_request_decision(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_deny("Reason")

        assert accumulator.permission_decision == "deny"
        assert accumulator.permission_request_decision is None

    def test_set_allow_does_not_affect_permission_request_decision(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_allow()

        assert accumulator.permission_decision == "allow"
        assert accumulator.permission_request_decision is None

    def test_add_warning_does_not_affect_permission_decisions(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.add_warning("Some warning")

        assert accumulator.permission_decision is None
        assert accumulator.permission_request_decision is None


class TestPermissionRequestDecisionIntegration:
    def test_permission_request_decision_allow_behavior(self) -> None:
        decision = PermissionRequestDecision(behavior="allow", message=None)

        assert decision.behavior == "allow"
        assert decision.message is None
        assert decision.interrupt is None

    def test_permission_request_decision_deny_with_all_fields(self) -> None:
        decision = PermissionRequestDecision(
            behavior="deny",
            message="Access denied",
            interrupt=True,
        )

        assert decision.behavior == "deny"
        assert decision.message == "Access denied"
        assert decision.interrupt is True

    def test_permission_request_decision_can_serialize(self) -> None:
        decision = PermissionRequestDecision(
            behavior="deny",
            message="Test",
            interrupt=False,
        )

        json_output = decision.to_output_json()
        assert "deny" in json_output
        assert "Test" in json_output
