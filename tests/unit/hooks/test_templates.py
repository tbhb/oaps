"""Unit tests for template substitution in hook action messages."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from oaps.enums import HookEventType
from oaps.hooks._context import HookContext
from oaps.hooks._inputs import PreToolUseInput, UserPromptSubmitInput
from oaps.hooks._templates import substitute_template

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
        session_id="test-session-id",
        transcript_path=str(transcript),
        permission_mode="default",
        hook_event_name="PreToolUse",
        cwd="/home/user/project",
        tool_name="Bash",
        tool_input={"command": "ls -la", "timeout": 5000},
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
        claude_session_id="claude-session-456",
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
        prompt="Please help me with this task",
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
        claude_session_id="claude-session-789",
        oaps_dir=tmp_path / ".oaps",
        oaps_state_file=tmp_path / ".oaps/state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


class TestSimpleVariableSubstitution:
    def test_tool_name_substitution(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash"

    def test_cwd_substitution(self, pre_tool_use_context: HookContext) -> None:
        template = "${cwd}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "/home/user/project"

    def test_session_id_substitution(self, pre_tool_use_context: HookContext) -> None:
        template = "${session_id}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "claude-session-456"

    def test_hook_type_substitution(self, pre_tool_use_context: HookContext) -> None:
        template = "${hook_type}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "pre_tool_use"

    def test_permission_mode_substitution(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${permission_mode}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "default"


class TestNestedAccessSubstitution:
    def test_tool_input_command(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_input.command}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "ls -la"

    def test_tool_input_timeout(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_input.timeout}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "5000"

    def test_tool_input_missing_field_returns_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${tool_input.missing}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""

    def test_tool_input_deeply_nested_missing_returns_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Only supports one level of nesting, so this should return empty
        template = "${tool_input.deep.nested}"
        result = substitute_template(template, pre_tool_use_context)

        # The pattern only supports one level of nesting, so this won't match
        # and will be left as-is or return empty
        assert result == "${tool_input.deep.nested}"


class TestMissingVariableSubstitution:
    def test_unknown_top_level_variable_returns_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${unknown}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""

    def test_unknown_nested_variable_returns_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${unknown.field}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""

    def test_tool_name_missing_in_non_tool_context(
        self, user_prompt_submit_context: HookContext
    ) -> None:
        # UserPromptSubmit doesn't have tool_name
        template = "${tool_name}"
        result = substitute_template(template, user_prompt_submit_context)

        assert result == ""

    def test_tool_input_missing_in_non_tool_context(
        self, user_prompt_submit_context: HookContext
    ) -> None:
        # UserPromptSubmit doesn't have tool_input
        template = "${tool_input.command}"
        result = substitute_template(template, user_prompt_submit_context)

        assert result == ""


class TestMultipleVariablesInTemplate:
    def test_two_variables(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name}: ${cwd}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash: /home/user/project"

    def test_three_variables(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name} in ${cwd} with command '${tool_input.command}'"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash in /home/user/project with command 'ls -la'"

    def test_duplicate_variables(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name} ${tool_name} ${tool_name}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash Bash Bash"

    def test_mixed_found_and_missing_variables(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${tool_name} ${unknown} ${cwd}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash  /home/user/project"


class TestEmptyTemplateHandling:
    def test_empty_string_returns_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = ""
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""

    def test_whitespace_only_returns_whitespace(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "   "
        result = substitute_template(template, pre_tool_use_context)

        # Should pass through unchanged (no variables to substitute)
        assert result == "   "


class TestTemplateWithNoVariables:
    def test_plain_text_returns_unchanged(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "This is plain text with no variables"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "This is plain text with no variables"

    def test_text_with_dollar_sign_but_no_braces(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "Cost is $100"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Cost is $100"

    def test_text_with_braces_but_no_dollar_sign(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "Use {curly} braces"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Use {curly} braces"


class TestPromptVariableSubstitution:
    def test_prompt_substitution(self, user_prompt_submit_context: HookContext) -> None:
        template = "User said: ${prompt}"
        result = substitute_template(template, user_prompt_submit_context)

        assert result == "User said: Please help me with this task"

    def test_prompt_missing_in_tool_context(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # PreToolUse doesn't have prompt
        template = "${prompt}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""


class TestSpecialCharactersInValues:
    def test_values_with_special_characters_preserved(
        self, mock_logger: MagicMock, tmp_path: Path
    ) -> None:
        transcript = tmp_path / "transcript.json"
        hook_input = PreToolUseInput(
            session_id="test-session",
            transcript_path=str(transcript),
            permission_mode="default",
            hook_event_name="PreToolUse",
            cwd="/path/with spaces/and-dashes",
            tool_name="Bash",
            tool_input={"command": "echo 'hello $USER'"},
            tool_use_id="tool-123",
        )
        context = HookContext(
            hook_event_type=HookEventType.PRE_TOOL_USE,
            hook_input=hook_input,
            claude_session_id="test-session",
            oaps_dir=tmp_path / ".oaps",
            oaps_state_file=tmp_path / ".oaps/state.db",
            hook_logger=mock_logger,
            session_logger=mock_logger,
        )

        template = "Running in ${cwd}: ${tool_input.command}"
        result = substitute_template(template, context)

        assert result == "Running in /path/with spaces/and-dashes: echo 'hello $USER'"


class TestVariableNamePatterns:
    def test_variable_with_underscore(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash"

    def test_variable_with_numbers_in_name(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Variable names can have numbers (after first character)
        # But our standard vars don't have numbers, so this tests unknown var
        template = "${var123}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == ""

    def test_invalid_variable_syntax_not_substituted(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Numbers at start not valid
        template = "${123var}"
        result = substitute_template(template, pre_tool_use_context)

        # Should not match the pattern, so left unchanged
        assert result == "${123var}"


class TestEdgeCases:
    def test_adjacent_variables(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name}${cwd}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash/home/user/project"

    def test_variable_at_start(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name} is the tool"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash is the tool"

    def test_variable_at_end(self, pre_tool_use_context: HookContext) -> None:
        template = "Tool is ${tool_name}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Tool is Bash"

    def test_only_variable(self, pre_tool_use_context: HookContext) -> None:
        template = "${tool_name}"
        result = substitute_template(template, pre_tool_use_context)

        assert result == "Bash"

    def test_nested_braces_not_supported(
        self, pre_tool_use_context: HookContext
    ) -> None:
        template = "${{tool_name}}"
        result = substitute_template(template, pre_tool_use_context)

        # Pattern won't match double braces
        assert result == "${{tool_name}}"
