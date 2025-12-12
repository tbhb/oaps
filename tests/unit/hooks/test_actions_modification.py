"""Unit tests for Phase 6 Modification Actions (ModifyAction, TransformAction)."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.config import HookRuleActionConfiguration
from oaps.enums import HookEventType
from oaps.hooks._action import (
    ModifyAction,
    OutputAccumulator,
    TransformAction,
)
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import (
    PermissionRequestInput,
    PreToolUseInput,
    SessionStartInput,
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
        cwd=str(tmp_path),  # Use tmp_path so subprocess can use it as cwd
        tool_name="Bash",
        tool_input={"command": "rm -rf /tmp/test", "timeout": 60},
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
        cwd=str(tmp_path),  # Use tmp_path so subprocess can use it as cwd
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
def session_start_input(tmp_path: Path) -> SessionStartInput:
    from uuid import UUID

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
def output_accumulator() -> OutputAccumulator:
    return OutputAccumulator()


def make_modify_config(
    *,
    field: str | None = None,
    operation: str | None = None,
    value: str | None = None,
    pattern: str | None = None,
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(
        type="modify",
        field=field,
        operation=operation,  # pyright: ignore[reportArgumentType]
        value=value,
        pattern=pattern,
    )


def make_transform_config(
    *,
    command: str | None = None,
    script: str | None = None,
    entrypoint: str | None = None,
    timeout_ms: int | None = None,
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(
        type="transform",
        command=command,
        script=script,
        entrypoint=entrypoint,
        timeout_ms=timeout_ms,
    )


class TestModifyAction:
    def test_set_operation_replaces_field_value(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="set",
            value="ls -la",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "ls -la"

    def test_append_operation_adds_to_end(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="append",
            value=" --verbose",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        expected_command = "rm -rf /tmp/test --verbose"
        assert output_accumulator.updated_input["command"] == expected_command

    def test_prepend_operation_adds_to_beginning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="prepend",
            value="sudo ",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "sudo rm -rf /tmp/test"

    def test_replace_operation_with_regex(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="replace",
            pattern=r"/tmp/\w+",  # noqa: S108
            value="/safe/directory",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "rm -rf /safe/directory"

    def test_replace_with_capture_groups(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="replace",
            pattern=r"rm -rf (/\S+)",
            value=r"echo 'Would remove: \1'",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert (
            output_accumulator.updated_input["command"]
            == "echo 'Would remove: /tmp/test'"
        )

    def test_template_substitution_in_value(
        self,
        pre_tool_use_input: PreToolUseInput,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="set",
            value="echo 'In ${cwd}'",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        expected_cwd = pre_tool_use_input.cwd
        assert (
            output_accumulator.updated_input["command"] == f"echo 'In {expected_cwd}'"
        )

    def test_only_modified_field_in_updated_input(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="set",
            value="ls",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "ls"
        # Only the modified field should be in updated_input
        assert "timeout" not in output_accumulator.updated_input

    def test_works_with_permission_request_context(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="file_path",
            operation="set",
            value="/safe/path/file.txt",
        )

        action.run(permission_request_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["file_path"] == "/safe/path/file.txt"

    def test_logs_warning_for_unsupported_hook_type(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="set",
            value="test",
        )

        action.run(session_start_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "unsupported hook type" in str(mock_logger.warning.call_args)
        assert output_accumulator.updated_input is None

    def test_logs_warning_when_field_missing(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            operation="set",
            value="test",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "no field specified" in str(mock_logger.warning.call_args)

    def test_logs_warning_when_operation_missing(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            value="test",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "no operation specified" in str(mock_logger.warning.call_args)

    def test_replace_without_pattern_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="replace",
            value="replacement",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "replace requires pattern" in str(mock_logger.warning.call_args)

    def test_invalid_regex_pattern_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="replace",
            pattern="[invalid(regex",
            value="replacement",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "invalid regex pattern" in str(mock_logger.warning.call_args)

    def test_append_on_non_string_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="timeout",  # This is an int
            operation="append",
            value="_suffix",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "append requires string field" in str(mock_logger.warning.call_args)

    def test_set_on_none_creates_field(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="new_field",
            operation="set",
            value="new_value",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["new_field"] == "new_value"

    def test_append_on_none_uses_value(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()
        config = make_modify_config(
            field="new_field",
            operation="append",
            value="value",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["new_field"] == "value"

    def test_does_not_mutate_original_context(
        self,
        pre_tool_use_input: PreToolUseInput,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        original_command = pre_tool_use_input.tool_input["command"]

        action = ModifyAction()
        config = make_modify_config(
            field="command",
            operation="set",
            value="completely different",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        # Original context should be unchanged
        assert pre_tool_use_input.tool_input["command"] == original_command

    def test_multiple_modify_actions_compose(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()

        # First modify action changes command
        config1 = make_modify_config(
            field="command",
            operation="set",
            value="modified_command",
        )
        action.run(pre_tool_use_context, config1, output_accumulator)

        # Second modify action adds a new field
        config2 = make_modify_config(
            field="extra_field",
            operation="set",
            value="extra_value",
        )
        action.run(pre_tool_use_context, config2, output_accumulator)

        # Both modifications should be present
        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "modified_command"
        assert output_accumulator.updated_input["extra_field"] == "extra_value"

    def test_second_modify_reads_from_accumulated_value(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = ModifyAction()

        # First modify action sets command
        config1 = make_modify_config(
            field="command",
            operation="set",
            value="first_value",
        )
        action.run(pre_tool_use_context, config1, output_accumulator)

        # Second modify action appends to command
        config2 = make_modify_config(
            field="command",
            operation="append",
            value="_appended",
        )
        action.run(pre_tool_use_context, config2, output_accumulator)

        # Result should be first value with append
        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "first_value_appended"


class TestTransformAction:
    def test_script_returns_transform_input(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command='echo \'{"transform_input": {"command": "safe_command"}}\'',
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "safe_command"

    def test_script_with_multiple_fields(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        json_output = '{"transform_input": {"command": "new_cmd", "extra": "field"}}'
        config = make_transform_config(command=f"echo '{json_output}'")

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "new_cmd"
        assert output_accumulator.updated_input["extra"] == "field"

    def test_empty_output_no_modification(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command="echo ''",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is None

    def test_json_without_transform_input_key(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command='echo \'{"other_key": "value"}\'',
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        # No transformation should occur when transform_input key is missing
        assert output_accumulator.updated_input is None

    def test_invalid_json_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command="echo 'not valid json'",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "invalid JSON" in str(mock_logger.warning.call_args)
        assert output_accumulator.updated_input is None

    def test_transform_input_not_dict_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command='echo \'{"transform_input": "not a dict"}\'',
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "transform_input is not a dict" in str(mock_logger.warning.call_args)
        assert output_accumulator.updated_input is None

    def test_timeout_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command="sleep 10",
            timeout_ms=100,  # 100ms timeout
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "timed out" in str(mock_logger.warning.call_args)

    def test_command_not_found_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command="nonexistent_command_xyz123",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "command not found" in str(mock_logger.warning.call_args)

    def test_logs_warning_for_unsupported_hook_type(
        self,
        session_start_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command="echo '{}'",
        )

        action.run(session_start_context, config, output_accumulator)

        mock_logger.warning.assert_called_once()
        assert "unsupported hook type" in str(mock_logger.warning.call_args)

    def test_no_command_or_entrypoint_returns_early(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = HookRuleActionConfiguration(type="transform")

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.debug.assert_called()
        assert output_accumulator.updated_input is None

    def test_works_with_permission_request_context(
        self,
        permission_request_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            command='echo \'{"transform_input": {"file_path": "/safe/path"}}\'',
        )

        action.run(permission_request_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["file_path"] == "/safe/path"

    def test_multiline_script(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            script="""#!/bin/sh
echo '{"transform_input": {"command": "from_script"}}'
""",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["command"] == "from_script"


class TestTransformActionPython:
    def test_python_transform_returns_transform_input(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
    ) -> None:
        # Use a built-in module that can return a dict
        action = TransformAction()
        config = make_transform_config(
            entrypoint="tests.unit.hooks.test_actions_modification:sample_transform",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        assert output_accumulator.updated_input is not None
        assert output_accumulator.updated_input["transformed"] is True

    def test_invalid_entrypoint_format_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            entrypoint="no_colon_here",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "invalid entrypoint format" in str(mock_logger.warning.call_args)

    def test_module_not_found_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            entrypoint="nonexistent.module:func",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "failed to import module" in str(mock_logger.warning.call_args)

    def test_function_not_found_logs_warning(
        self,
        pre_tool_use_context: HookContext,
        output_accumulator: OutputAccumulator,
        mock_logger: MagicMock,
    ) -> None:
        action = TransformAction()
        config = make_transform_config(
            entrypoint="os:nonexistent_function_xyz",
        )

        action.run(pre_tool_use_context, config, output_accumulator)

        mock_logger.warning.assert_called()
        assert "function not found" in str(mock_logger.warning.call_args)


class TestOutputAccumulatorUpdatedInput:
    def test_set_updated_input_creates_dict_if_none(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_updated_input({"key": "value"})

        assert accumulator.updated_input is not None
        assert accumulator.updated_input["key"] == "value"

    def test_set_updated_input_merges_into_existing(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_updated_input({"key1": "value1"})
        accumulator.set_updated_input({"key2": "value2"})

        assert accumulator.updated_input is not None
        assert accumulator.updated_input["key1"] == "value1"
        assert accumulator.updated_input["key2"] == "value2"

    def test_set_updated_input_overwrites_existing_key(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_updated_input({"key": "original"})
        accumulator.set_updated_input({"key": "updated"})

        assert accumulator.updated_input is not None
        assert accumulator.updated_input["key"] == "updated"

    def test_updated_input_does_not_affect_other_fields(self) -> None:
        accumulator = OutputAccumulator()
        accumulator.set_updated_input({"key": "value"})

        assert accumulator.permission_decision is None
        assert accumulator.permission_request_decision is None
        assert len(accumulator.system_messages) == 0
        assert len(accumulator.additional_context_items) == 0


# Sample transform function for Python transform tests
def sample_transform(context: object) -> dict[str, object]:
    """Sample transform function that returns a transform_input dict."""
    del context  # Unused
    return {"transform_input": {"transformed": True}}
