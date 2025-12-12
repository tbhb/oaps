from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest

from oaps.config import HookRuleActionConfiguration, HookRuleConfiguration, RulePriority
from oaps.enums import HookEventType
from oaps.hooks import (
    ActionResult,
    ExecutionResult,
    MatchedRule,
    PreToolUseInput,
    execute_rules,
)
from oaps.hooks._context import HookContext

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def mock_logger() -> MagicMock:
    from unittest.mock import MagicMock

    logger = MagicMock()
    # Ensure debug and warning methods exist
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


def make_action(
    action_type: Literal["log", "python", "shell"] = "log",
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(type=action_type)


EventType = Literal[
    "all",
    "pre_tool_use",
    "post_tool_use",
    "permission_request",
    "user_prompt_submit",
    "notification",
    "session_start",
    "session_end",
    "stop",
    "subagent_stop",
    "pre_compact",
]


def make_rule(
    rule_id: str,
    events: set[EventType],
    *,
    condition: str = "",
    priority: RulePriority = RulePriority.MEDIUM,
    enabled: bool = True,
    result: Literal["block", "ok", "warn"] = "ok",
    terminal: bool = False,
    description: str | None = None,
    actions: list[HookRuleActionConfiguration] | None = None,
) -> HookRuleConfiguration:
    return HookRuleConfiguration(
        id=rule_id,
        events=events,
        condition=condition,
        priority=priority,
        enabled=enabled,
        result=result,
        terminal=terminal,
        description=description,
        actions=actions or [],
    )


def make_matched_rule(
    rule: HookRuleConfiguration,
    match_order: int = 0,
) -> MatchedRule:
    return MatchedRule(rule=rule, match_order=match_order)


class TestActionExecution:
    def test_actions_are_executed_in_order(
        self, pre_tool_use_context: HookContext
    ) -> None:
        actions = [make_action("log"), make_action("log"), make_action("log")]
        rule = make_rule("test-rule", {"pre_tool_use"}, result="ok", actions=actions)
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert len(result.rule_results[0].action_results) == 3

    def test_action_result_captures_success(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            result="ok",
            actions=[make_action("log")],
        )
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert len(result.rule_results) == 1
        action_result = result.rule_results[0].action_results[0]
        assert action_result.success is True
        assert action_result.error is None

    def test_action_result_structure(self, pre_tool_use_context: HookContext) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            result="ok",
            actions=[make_action("log")],
        )
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        action_result = result.rule_results[0].action_results[0]
        assert isinstance(action_result, ActionResult)
        assert action_result.action_type == "log"


class TestFailOpenBehavior:
    def test_execution_continues_after_action_failure(
        self, pre_tool_use_context: HookContext, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Patch the permission action handler to raise an exception
        from oaps.hooks import _executor

        original_get_handler = _executor._get_permission_action_handler

        call_count = 0

        def mock_get_handler(action_type: str) -> object:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call raises
                class FailingAction:
                    def run(
                        self, context: object, config: object, accumulator: object
                    ) -> None:
                        msg = "Test error"
                        raise RuntimeError(msg)

                return FailingAction()
            return original_get_handler(action_type)

        monkeypatch.setattr(
            _executor, "_get_permission_action_handler", mock_get_handler
        )

        # Use shell action which is now a permission action
        actions = [make_action("shell"), make_action("shell")]
        rule = make_rule("test-rule", {"pre_tool_use"}, result="ok", actions=actions)
        matched = make_matched_rule(rule)

        result = execute_rules([matched], pre_tool_use_context)

        # Both actions should be attempted
        assert len(result.rule_results[0].action_results) == 2
        # First failed
        assert result.rule_results[0].action_results[0].success is False
        assert result.rule_results[0].action_results[0].error == "Test error"
        # Second succeeded
        assert result.rule_results[0].action_results[1].success is True

    def test_action_errors_are_logged(
        self,
        pre_tool_use_context: HookContext,
        mock_logger: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from oaps.hooks import _executor

        class FailingAction:
            def run(self, context: object, config: object, accumulator: object) -> None:
                msg = "Test error"
                raise RuntimeError(msg)

        def get_failing_action(_action_type: str) -> FailingAction:
            return FailingAction()

        monkeypatch.setattr(
            _executor, "_get_permission_action_handler", get_failing_action
        )

        # Use shell action which is now a permission action
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            result="ok",
            actions=[make_action("shell")],
        )
        matched = make_matched_rule(rule)
        execute_rules([matched], pre_tool_use_context)

        mock_logger.warning.assert_called()  # pyright: ignore[reportAny]


class TestResultAggregation:
    def test_should_block_true_if_any_rule_has_result_block(
        self, pre_tool_use_context: HookContext
    ) -> None:
        ok_rule = make_rule("ok-rule", {"pre_tool_use"}, result="ok")
        block_rule = make_rule("block-rule", {"pre_tool_use"}, result="block")
        matched_rules = [
            make_matched_rule(ok_rule, match_order=0),
            make_matched_rule(block_rule, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert result.should_block is True

    def test_should_block_false_if_no_rule_blocks(
        self, pre_tool_use_context: HookContext
    ) -> None:
        ok_rule = make_rule("ok-rule", {"pre_tool_use"}, result="ok")
        warn_rule = make_rule("warn-rule", {"pre_tool_use"}, result="warn")
        matched_rules = [
            make_matched_rule(ok_rule, match_order=0),
            make_matched_rule(warn_rule, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert result.should_block is False

    def test_block_reason_comes_from_first_blocking_rule(
        self, pre_tool_use_context: HookContext
    ) -> None:
        block_rule_1 = make_rule(
            "block-1",
            {"pre_tool_use"},
            result="block",
            description="First block reason",
        )
        block_rule_2 = make_rule(
            "block-2",
            {"pre_tool_use"},
            result="block",
            description="Second block reason",
        )
        matched_rules = [
            make_matched_rule(block_rule_1, match_order=0),
            make_matched_rule(block_rule_2, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert result.block_reason == "First block reason"

    def test_block_reason_uses_rule_id_when_no_description(
        self, pre_tool_use_context: HookContext
    ) -> None:
        block_rule = make_rule(
            "my-block-rule",
            {"pre_tool_use"},
            result="block",
            description=None,
        )
        matched = make_matched_rule(block_rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert result.block_reason == "Blocked by rule: my-block-rule"

    def test_warnings_collect_messages_from_warn_rules(
        self, pre_tool_use_context: HookContext
    ) -> None:
        warn_rule_1 = make_rule(
            "warn-1",
            {"pre_tool_use"},
            result="warn",
            description="Warning 1",
        )
        warn_rule_2 = make_rule(
            "warn-2",
            {"pre_tool_use"},
            result="warn",
            description="Warning 2",
        )
        matched_rules = [
            make_matched_rule(warn_rule_1, match_order=0),
            make_matched_rule(warn_rule_2, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert len(result.warnings) == 2
        assert "Warning 1" in result.warnings
        assert "Warning 2" in result.warnings

    def test_warnings_use_rule_id_when_no_description(
        self, pre_tool_use_context: HookContext
    ) -> None:
        warn_rule = make_rule(
            "my-warn-rule",
            {"pre_tool_use"},
            result="warn",
            description=None,
        )
        matched = make_matched_rule(warn_rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert "Warning from rule: my-warn-rule" in result.warnings

    def test_ok_rules_do_not_produce_warnings_or_blocks(
        self, pre_tool_use_context: HookContext
    ) -> None:
        ok_rule = make_rule(
            "ok-rule",
            {"pre_tool_use"},
            result="ok",
            description="Just OK",
        )
        matched = make_matched_rule(ok_rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert result.should_block is False
        assert result.block_reason is None
        assert len(result.warnings) == 0


class TestTerminalRules:
    def test_execution_stops_after_terminal_rule(
        self, pre_tool_use_context: HookContext
    ) -> None:
        terminal_rule = make_rule(
            "terminal-rule", {"pre_tool_use"}, result="ok", terminal=True
        )
        after_rule = make_rule(
            "after-rule", {"pre_tool_use"}, result="ok", terminal=False
        )
        matched_rules = [
            make_matched_rule(terminal_rule, match_order=0),
            make_matched_rule(after_rule, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        # Only the terminal rule should be executed
        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "terminal-rule"

    def test_terminated_early_is_true_when_stopped_by_terminal_rule(
        self, pre_tool_use_context: HookContext
    ) -> None:
        terminal_rule = make_rule(
            "terminal-rule", {"pre_tool_use"}, result="ok", terminal=True
        )
        after_rule = make_rule(
            "after-rule", {"pre_tool_use"}, result="ok", terminal=False
        )
        matched_rules = [
            make_matched_rule(terminal_rule, match_order=0),
            make_matched_rule(after_rule, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert result.terminated_early is True

    def test_non_terminal_rules_do_not_stop_execution(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule_1 = make_rule("rule-1", {"pre_tool_use"}, result="ok", terminal=False)
        rule_2 = make_rule("rule-2", {"pre_tool_use"}, result="ok", terminal=False)
        rule_3 = make_rule("rule-3", {"pre_tool_use"}, result="ok", terminal=False)
        matched_rules = [
            make_matched_rule(rule_1, match_order=0),
            make_matched_rule(rule_2, match_order=1),
            make_matched_rule(rule_3, match_order=2),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert len(result.rule_results) == 3
        assert result.terminated_early is False

    def test_terminal_blocking_rule_sets_both_flags(
        self, pre_tool_use_context: HookContext
    ) -> None:
        terminal_block = make_rule(
            "terminal-block",
            {"pre_tool_use"},
            result="block",
            terminal=True,
            description="Blocked and stopped",
        )
        after_rule = make_rule(
            "after-rule", {"pre_tool_use"}, result="ok", terminal=False
        )
        matched_rules = [
            make_matched_rule(terminal_block, match_order=0),
            make_matched_rule(after_rule, match_order=1),
        ]
        result = execute_rules(matched_rules, pre_tool_use_context)

        assert result.should_block is True
        assert result.terminated_early is True
        assert result.block_reason == "Blocked and stopped"


class TestEmptyRules:
    def test_empty_matched_rules_returns_empty_execution_result(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = execute_rules([], pre_tool_use_context)

        assert isinstance(result, ExecutionResult)
        assert len(result.rule_results) == 0

    def test_empty_rules_should_block_is_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = execute_rules([], pre_tool_use_context)
        assert result.should_block is False

    def test_empty_rules_terminated_early_is_false(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = execute_rules([], pre_tool_use_context)
        assert result.terminated_early is False

    def test_empty_rules_block_reason_is_none(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = execute_rules([], pre_tool_use_context)
        assert result.block_reason is None

    def test_empty_rules_warnings_is_empty(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = execute_rules([], pre_tool_use_context)
        assert len(result.warnings) == 0


class TestRuleExecutionResultStructure:
    def test_rule_execution_result_contains_rule_id(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("my-rule-id", {"pre_tool_use"}, result="ok")
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert result.rule_results[0].rule_id == "my-rule-id"

    def test_rule_execution_result_contains_result_type(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, result="warn")
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert result.rule_results[0].result_type == "warn"

    def test_rule_execution_result_contains_is_terminal(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, result="ok", terminal=True)
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert result.rule_results[0].is_terminal is True

    def test_rule_execution_result_action_results_are_tuple(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            result="ok",
            actions=[make_action("log"), make_action("log")],
        )
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert isinstance(result.rule_results[0].action_results, tuple)
        assert len(result.rule_results[0].action_results) == 2


class TestExecutionResultStructure:
    def test_execution_result_rule_results_are_tuple(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, result="ok")
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert isinstance(result.rule_results, tuple)

    def test_execution_result_warnings_are_tuple(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            result="warn",
            description="Warning",
        )
        matched = make_matched_rule(rule)
        result = execute_rules([matched], pre_tool_use_context)

        assert isinstance(result.warnings, tuple)


class TestUnknownActionType:
    def test_unknown_action_type_uses_noop_handler(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Create a rule with an action that has an unknown type
        # We need to construct this manually since Pydantic validates the type
        from oaps.hooks._action import NoOpAction
        from oaps.hooks._executor import _get_action_handler

        handler = _get_action_handler("unknown_action_type")
        assert isinstance(handler, NoOpAction)
