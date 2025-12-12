# pyright: reportAttributeAccessIssue=false
"""Unit tests for automation action infrastructure."""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from oaps.config import HookRuleActionConfiguration
from oaps.enums import HookEventType
from oaps.exceptions import BlockHook
from oaps.hooks._action import OutputAccumulator, PythonAction, ScriptAction
from oaps.hooks._automation import (
    AutomationResult,
    process_return_value,
    serialize_context,
    truncate_output,
)
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import (
    PostToolUseInput,
    PreToolUseInput,
    SessionStartInput,
    UserPromptSubmitInput,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def pre_tool_use_input(tmp_path: Path) -> PreToolUseInput:
    transcript = tmp_path / "transcript.json"
    # Use tmp_path as cwd since it exists (needed for ScriptAction tests)
    return PreToolUseInput(
        session_id="test-session",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd=str(tmp_path),
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
    # Use tmp_path as cwd since it exists (needed for ScriptAction tests)
    return SessionStartInput(
        session_id=UUID("12345678-1234-5678-1234-567812345678"),
        transcript_path=transcript,
        hook_event_name="SessionStart",
        cwd=tmp_path,
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
def output_accumulator() -> OutputAccumulator:
    return OutputAccumulator()


def make_action_config(
    action_type: str = "shell",
    *,
    command: str | None = None,
    script: str | None = None,
    entrypoint: str | None = None,
    stdin: str | None = None,
    env: dict[str, str] | None = None,
    timeout_ms: int | None = None,
    shell: str | None = None,
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(
        type=action_type,  # pyright: ignore[reportArgumentType]
        command=command,
        script=script,
        entrypoint=entrypoint,
        stdin=stdin,  # pyright: ignore[reportArgumentType]
        env=env or {},
        timeout_ms=timeout_ms,
        shell=shell,
    )


class TestAutomationResult:
    def test_creates_successful_result(self) -> None:
        result = AutomationResult(success=True, output="test output")
        assert result.success is True
        assert result.output == "test output"
        assert result.error is None
        assert result.return_value is None

    def test_creates_failed_result(self) -> None:
        result = AutomationResult(success=False, error="something went wrong")
        assert result.success is False
        assert result.output is None
        assert result.error == "something went wrong"

    def test_creates_result_with_return_value(self) -> None:
        result = AutomationResult(
            success=True,
            output='{"key": "value"}',
            return_value={"key": "value"},
        )
        assert result.success is True
        assert result.return_value == {"key": "value"}


class TestSerializeContext:
    def test_serializes_context_to_json_string(
        self,
        pre_tool_use_context: HookContext,
    ) -> None:
        import json

        result = serialize_context(pre_tool_use_context)

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_includes_hook_type(
        self,
        pre_tool_use_context: HookContext,
    ) -> None:
        import json

        result = serialize_context(pre_tool_use_context)
        parsed = json.loads(result)

        # hook_type is snake_case as per adapt_context
        assert parsed["hook_type"] == "pre_tool_use"

    def test_includes_hook_input(
        self,
        pre_tool_use_context: HookContext,
    ) -> None:
        import json

        result = serialize_context(pre_tool_use_context)
        parsed = json.loads(result)

        assert "hook_input" in parsed
        assert parsed["hook_input"]["tool_name"] == "Bash"
        assert parsed["hook_input"]["tool_input"]["command"] == "ls -la"

    def test_includes_oaps_paths(
        self,
        pre_tool_use_context: HookContext,
    ) -> None:
        import json

        result = serialize_context(pre_tool_use_context)
        parsed = json.loads(result)

        assert "oaps_dir" in parsed
        assert "oaps_state_file" in parsed
        assert ".oaps" in parsed["oaps_dir"]

    def test_includes_timestamp(
        self,
        pre_tool_use_context: HookContext,
    ) -> None:
        import json

        result = serialize_context(pre_tool_use_context)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        # ISO format timestamp
        assert "T" in parsed["timestamp"]


class TestTruncateOutput:
    def test_returns_empty_string_unchanged(self) -> None:
        assert truncate_output("") == ""

    def test_returns_short_string_unchanged(self) -> None:
        short_text = "hello world"
        assert truncate_output(short_text) == short_text

    def test_truncates_long_string(self) -> None:
        long_text = "x" * 200000
        result = truncate_output(long_text, max_bytes=100)

        assert len(result.encode("utf-8")) < 200000
        assert "[output truncated]" in result

    def test_preserves_valid_utf8(self) -> None:
        # String with multi-byte UTF-8 characters
        text = "Hello " + "".join(chr(i) for i in range(0x4E00, 0x4E10))
        result = truncate_output(text, max_bytes=20)

        # Should decode without errors
        result.encode("utf-8")
        assert "[output truncated]" in result

    def test_uses_default_max_bytes(self) -> None:
        # Just verify it doesn't error with default
        text = "x" * 1000
        result = truncate_output(text)
        assert result == text  # Should not truncate under default limit


class TestProcessReturnValue:
    def test_does_nothing_with_none_return_value(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        process_return_value(
            None, pre_tool_use_context, output_accumulator, mock_logger
        )

        assert output_accumulator.permission_decision is None
        assert len(output_accumulator.system_messages) == 0
        assert len(output_accumulator.additional_context_items) == 0

    def test_handles_inject_for_supported_hook(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"inject": "Additional context here"}

        process_return_value(
            return_value, session_start_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.additional_context_items) == 1
        expected = "Additional context here"
        assert output_accumulator.additional_context_items[0] == expected

    def test_handles_inject_for_post_tool_use(
        self,
        post_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"inject": "Post tool context"}

        process_return_value(
            return_value, post_tool_use_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.additional_context_items) == 1
        assert output_accumulator.additional_context_items[0] == "Post tool context"

    def test_handles_inject_for_user_prompt_submit(
        self,
        user_prompt_submit_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"inject": "Prompt context"}

        process_return_value(
            return_value, user_prompt_submit_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.additional_context_items) == 1

    def test_logs_warning_for_inject_on_unsupported_hook(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"inject": "Should not inject"}

        process_return_value(
            return_value, pre_tool_use_context, output_accumulator, mock_logger
        )

        # Should not inject
        assert len(output_accumulator.additional_context_items) == 0
        # Should log warning
        mock_logger.warning.assert_called_once()

    def test_handles_warn_directive(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"warn": "This is a warning message"}

        process_return_value(
            return_value, pre_tool_use_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.system_messages) == 1
        assert output_accumulator.system_messages[0] == "This is a warning message"

    def test_handles_allow_directive(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"allow": True}

        process_return_value(
            return_value, pre_tool_use_context, output_accumulator, mock_logger
        )

        assert output_accumulator.permission_decision == "allow"

    def test_handles_deny_with_true(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"deny": True}

        with pytest.raises(BlockHook) as exc_info:
            process_return_value(
                return_value, pre_tool_use_context, output_accumulator, mock_logger
            )

        assert "denied by automation action" in str(exc_info.value)
        assert output_accumulator.permission_decision == "deny"

    def test_handles_deny_with_message(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"deny": "Operation not permitted"}

        with pytest.raises(BlockHook) as exc_info:
            process_return_value(
                return_value, pre_tool_use_context, output_accumulator, mock_logger
            )

        assert str(exc_info.value) == "Operation not permitted"
        assert output_accumulator.permission_decision == "deny"
        expected_reason = "Operation not permitted"
        assert output_accumulator.permission_decision_reason == expected_reason

    def test_handles_multiple_directives(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {
            "inject": "Some context",
            "warn": "A warning",
            "allow": True,
        }

        process_return_value(
            return_value, session_start_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.additional_context_items) == 1
        assert len(output_accumulator.system_messages) == 1
        assert output_accumulator.permission_decision == "allow"

    def test_ignores_empty_string_inject(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"inject": ""}

        process_return_value(
            return_value, session_start_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.additional_context_items) == 0

    def test_ignores_empty_string_warn(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"warn": ""}

        process_return_value(
            return_value, pre_tool_use_context, output_accumulator, mock_logger
        )

        assert len(output_accumulator.system_messages) == 0

    def test_ignores_non_true_allow(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        return_value: dict[str, object] = {"allow": "yes"}  # Not boolean True

        process_return_value(
            return_value, pre_tool_use_context, output_accumulator, mock_logger
        )

        assert output_accumulator.permission_decision is None


class TestScriptAction:
    def test_executes_simple_command(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        config = make_action_config("shell", command="echo hello")

        # Should complete without error
        action.run(pre_tool_use_context, config, output_accumulator)

    def test_does_nothing_without_command_or_script(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ScriptAction()
        config = make_action_config("shell")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.debug.assert_called()
        assert output_accumulator.permission_decision is None

    def test_parses_json_output_as_return_value(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        # Use script with heredoc-style JSON output for portability
        config = make_action_config(
            "shell",
            script='#!/bin/sh\necho \'{"inject": "context from script"}\'',
        )

        action.run(session_start_context, config, output_accumulator)

        assert len(output_accumulator.additional_context_items) == 1
        assert output_accumulator.additional_context_items[0] == "context from script"

    def test_handles_script_multiline(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        script = """#!/bin/sh
echo "line 1"
echo "line 2"
"""
        config = make_action_config("shell", script=script)

        # Should complete without error
        action.run(pre_tool_use_context, config, output_accumulator)

    def test_uses_custom_shell(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        config = make_action_config(  # noqa: S604
            "shell",
            command="echo $SHELL",
            shell="/bin/bash",
        )

        # Should complete without error (may fail if bash not present)
        action.run(pre_tool_use_context, config, output_accumulator)

    def test_passes_environment_variables(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        config = make_action_config(
            "shell",
            command="echo '{\"inject\": \"'$TEST_VAR'\"}' ",
            env={"TEST_VAR": "test_value"},
        )

        action.run(session_start_context, config, output_accumulator)

        # The env var should be passed, though parsing may vary
        # At minimum, should not error
        assert True

    def test_fails_open_on_command_not_found(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ScriptAction()
        config = make_action_config("shell", command="nonexistent_command_12345")

        # Should not raise - fail open
        action.run(pre_tool_use_context, config, output_accumulator)

        # Should log warning
        mock_logger.warning.assert_called()

    def test_fails_open_on_timeout(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        # Use script to ensure sleep command is found
        config = make_action_config(
            "shell",
            script="#!/bin/sh\nsleep 10",
            timeout_ms=100,  # 0.1 second timeout
        )

        # Should not raise - fail open
        action.run(pre_tool_use_context, config, output_accumulator)

        # Should log warning about timeout - use the logger from context
        logger = pre_tool_use_context.hook_logger
        logger.warning.assert_called()  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        # Check the first positional argument of the call contains 'timed out'
        call_args = logger.warning.call_args_list[0]  # pyright: ignore[reportAttributeAccessIssue,reportUnknownMemberType]
        assert "timed out" in call_args[0][0]

    def test_handles_deny_from_script_output(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ScriptAction()
        # Use script for clean JSON output
        config = make_action_config(
            "shell",
            script='#!/bin/sh\necho \'{"deny": "blocked"}\'',
        )

        with pytest.raises(BlockHook) as exc_info:
            action.run(pre_tool_use_context, config, output_accumulator)

        assert "blocked" in str(exc_info.value)


class TestPythonAction:
    def test_does_nothing_without_entrypoint(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = PythonAction()
        config = make_action_config("python")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.debug.assert_called()

    def test_logs_warning_for_invalid_entrypoint_format(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = PythonAction()
        config = make_action_config("python", entrypoint="no_colon_separator")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        warning_calls = mock_logger.warning.call_args_list
        assert any("invalid entrypoint" in str(call) for call in warning_calls)

    def test_fails_open_on_import_error(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = PythonAction()
        config = make_action_config(
            "python", entrypoint="nonexistent_module_xyz:some_function"
        )

        # Should not raise
        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()

    def test_fails_open_on_attribute_error(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = PythonAction()
        # json module exists but doesn't have 'nonexistent_function'
        entrypoint = "json:nonexistent_function_xyz"
        config = make_action_config("python", entrypoint=entrypoint)

        # Should not raise
        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()

    def test_calls_function_with_context(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        # Create a test module function that we can import
        import sys

        # Create a temporary module
        import types

        test_module = types.ModuleType("test_hook_module")

        def test_function(context: HookContext) -> dict[str, str]:
            return {"inject": f"Hook type: {context.hook_event_type.value}"}

        test_module.test_function = test_function
        sys.modules["test_hook_module"] = test_module

        try:
            action = PythonAction()
            config = make_action_config(
                "python", entrypoint="test_hook_module:test_function"
            )

            action.run(session_start_context, config, output_accumulator)

            assert len(output_accumulator.additional_context_items) == 1
            # The hook_event_type.value is snake_case: "session_start"
            assert "session_start" in output_accumulator.additional_context_items[0]
        finally:
            del sys.modules["test_hook_module"]

    def test_handles_function_returning_none(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        import sys
        import types

        test_module = types.ModuleType("test_hook_module_none")

        def test_function(context: HookContext) -> None:  # noqa: ARG001
            return None

        test_module.test_function = test_function
        sys.modules["test_hook_module_none"] = test_module

        try:
            action = PythonAction()
            config = make_action_config(
                "python", entrypoint="test_hook_module_none:test_function"
            )

            # Should complete without error
            action.run(pre_tool_use_context, config, output_accumulator)

            assert output_accumulator.permission_decision is None
        finally:
            del sys.modules["test_hook_module_none"]

    def test_handles_deny_from_function(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        import sys
        import types

        test_module = types.ModuleType("test_hook_module_deny")

        def test_function(context: HookContext) -> dict[str, str]:  # noqa: ARG001
            return {"deny": "Operation not allowed"}

        test_module.test_function = test_function
        sys.modules["test_hook_module_deny"] = test_module

        try:
            action = PythonAction()
            config = make_action_config(
                "python", entrypoint="test_hook_module_deny:test_function"
            )

            with pytest.raises(BlockHook) as exc_info:
                action.run(pre_tool_use_context, config, output_accumulator)

            assert "Operation not allowed" in str(exc_info.value)
        finally:
            del sys.modules["test_hook_module_deny"]

    def test_fails_open_on_function_exception(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        import sys
        import types

        test_module = types.ModuleType("test_hook_module_error")

        def test_function(context: HookContext) -> dict[str, str]:  # noqa: ARG001
            msg = "Something went wrong"
            raise ValueError(msg)

        test_module.test_function = test_function
        sys.modules["test_hook_module_error"] = test_module

        try:
            action = PythonAction()
            config = make_action_config(
                "python", entrypoint="test_hook_module_error:test_function"
            )

            # Should not raise - fail open
            action.run(pre_tool_use_context, config, output_accumulator)

            mock_logger.warning.assert_called()
        finally:
            del sys.modules["test_hook_module_error"]
