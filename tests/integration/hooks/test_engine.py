"""Integration tests for the Phase 2 Rule Execution Engine.

These tests verify end-to-end rule execution from matching through execution,
combining match_rules() and execute_rules() in realistic scenarios.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest

from oaps.config import HookRuleActionConfiguration, HookRuleConfiguration, RulePriority
from oaps.enums import HookEventType
from oaps.hooks import (
    ExecutionResult,
    PreToolUseInput,
    execute_rules,
    match_rules,
)
from oaps.hooks._context import HookContext

if TYPE_CHECKING:
    from unittest.mock import MagicMock


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
        tool_input={"command": "rm -rf /"},
        tool_use_id="tool-123",
    )


@pytest.fixture
def pre_tool_use_context(
    pre_tool_use_input: PreToolUseInput,
    mock_logger: MagicMock,
    tmp_path: Path,
) -> HookContext:
    oaps_dir = tmp_path / ".oaps"
    oaps_dir.mkdir(parents=True, exist_ok=True)
    return HookContext(
        hook_event_type=HookEventType.PRE_TOOL_USE,
        hook_input=pre_tool_use_input,
        claude_session_id="test-session",
        oaps_dir=oaps_dir,
        oaps_state_file=oaps_dir / "state.db",
        hook_logger=mock_logger,
        session_logger=mock_logger,
    )


def make_action(
    action_type: Literal["log", "python", "shell"] = "log",
) -> HookRuleActionConfiguration:
    return HookRuleActionConfiguration(type=action_type)


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


def run_engine(
    rules: list[HookRuleConfiguration],
    context: HookContext,
) -> ExecutionResult:
    """Run the full rule engine: match_rules -> execute_rules."""
    matched = match_rules(rules, context)
    return execute_rules(matched, context)


class TestEndToEndRuleExecution:
    def test_single_matching_rule_executes_successfully(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "bash-audit",
                {"pre_tool_use"},
                condition='tool_name == "Bash"',
                result="ok",
                actions=[make_action("log")],
            )
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "bash-audit"
        assert result.should_block is False
        assert result.terminated_early is False

    def test_non_matching_rules_are_not_executed(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "read-only",
                {"pre_tool_use"},
                condition='tool_name == "Read"',
                result="ok",
            ),
            make_rule(
                "write-only",
                {"post_tool_use"},
                condition='tool_name == "Write"',
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 0
        assert result.should_block is False

    def test_full_flow_with_multiple_actions(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "complex-rule",
                {"pre_tool_use"},
                condition='tool_name == "Bash"',
                result="warn",
                description="Bash command detected",
                actions=[
                    make_action("log"),
                    make_action("log"),
                    make_action("log"),
                ],
            )
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert len(result.rule_results[0].action_results) == 3
        assert all(ar.success for ar in result.rule_results[0].action_results)
        assert "Bash command detected" in result.warnings


class TestMultipleRuleMatching:
    def test_multiple_rules_match_same_event(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "rule-1",
                {"pre_tool_use"},
                condition='tool_name == "Bash"',
                result="ok",
            ),
            make_rule(
                "rule-2",
                {"pre_tool_use"},
                condition='permission_mode == "default"',
                result="ok",
            ),
            make_rule(
                "rule-3",
                {"all"},
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 3
        rule_ids = [r.rule_id for r in result.rule_results]
        assert "rule-1" in rule_ids
        assert "rule-2" in rule_ids
        assert "rule-3" in rule_ids

    def test_rules_executed_in_correct_priority_order(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "low-priority",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="ok",
            ),
            make_rule(
                "critical-priority",
                {"pre_tool_use"},
                priority=RulePriority.CRITICAL,
                result="ok",
            ),
            make_rule(
                "high-priority",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="ok",
            ),
            make_rule(
                "medium-priority",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 4
        # Verify execution order: critical -> high -> medium -> low
        assert result.rule_results[0].rule_id == "critical-priority"
        assert result.rule_results[1].rule_id == "high-priority"
        assert result.rule_results[2].rule_id == "medium-priority"
        assert result.rule_results[3].rule_id == "low-priority"

    def test_definition_order_preserved_within_same_priority(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "medium-first",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
            ),
            make_rule(
                "medium-second",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
            ),
            make_rule(
                "medium-third",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 3
        assert result.rule_results[0].rule_id == "medium-first"
        assert result.rule_results[1].rule_id == "medium-second"
        assert result.rule_results[2].rule_id == "medium-third"

    def test_all_matching_rules_have_actions_executed(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "rule-with-actions-1",
                {"pre_tool_use"},
                result="ok",
                actions=[make_action("log"), make_action("log")],
            ),
            make_rule(
                "rule-with-actions-2",
                {"pre_tool_use"},
                result="ok",
                actions=[make_action("log")],
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 2
        assert len(result.rule_results[0].action_results) == 2
        assert len(result.rule_results[1].action_results) == 1


class TestTerminalRuleBehavior:
    def test_terminal_rule_stops_processing_subsequent_rules(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "first-rule",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="ok",
                terminal=True,
            ),
            make_rule(
                "second-rule",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
            ),
            make_rule(
                "third-rule",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "first-rule"
        assert result.terminated_early is True

    def test_non_terminal_rules_allow_subsequent_rules(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "first-rule",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="ok",
                terminal=False,
            ),
            make_rule(
                "second-rule",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
                terminal=False,
            ),
            make_rule(
                "third-rule",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="ok",
                terminal=False,
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 3
        assert result.terminated_early is False

    def test_terminal_rule_in_middle_stops_remaining(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "high-non-terminal",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="ok",
                terminal=False,
            ),
            make_rule(
                "medium-terminal",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="ok",
                terminal=True,
            ),
            make_rule(
                "low-non-terminal",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="ok",
                terminal=False,
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 2
        assert result.rule_results[0].rule_id == "high-non-terminal"
        assert result.rule_results[1].rule_id == "medium-terminal"
        assert result.terminated_early is True

    def test_terminal_blocking_rule_blocks_and_stops(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "terminal-blocker",
                {"pre_tool_use"},
                priority=RulePriority.CRITICAL,
                result="block",
                terminal=True,
                description="Dangerous command blocked",
            ),
            make_rule(
                "would-warn",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="warn",
                description="This warning should not appear",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert result.should_block is True
        assert result.block_reason == "Dangerous command blocked"
        assert result.terminated_early is True
        assert len(result.warnings) == 0


class TestMixedResultsAggregation:
    def test_mix_of_block_warn_and_ok_rules(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "ok-rule",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="ok",
            ),
            make_rule(
                "warn-rule",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="warn",
                description="Warning from medium rule",
            ),
            make_rule(
                "block-rule",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="block",
                description="Block from low rule",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 3
        assert result.should_block is True
        assert result.block_reason == "Block from low rule"
        assert len(result.warnings) == 1
        assert "Warning from medium rule" in result.warnings

    def test_multiple_warnings_aggregated(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "warn-1",
                {"pre_tool_use"},
                result="warn",
                description="First warning",
            ),
            make_rule(
                "warn-2",
                {"pre_tool_use"},
                result="warn",
                description="Second warning",
            ),
            make_rule(
                "warn-3",
                {"pre_tool_use"},
                result="warn",
                description="Third warning",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert result.should_block is False
        assert len(result.warnings) == 3
        assert "First warning" in result.warnings
        assert "Second warning" in result.warnings
        assert "Third warning" in result.warnings

    def test_first_blocking_rule_sets_block_reason(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "block-high",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="block",
                description="High priority block",
            ),
            make_rule(
                "block-medium",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                result="block",
                description="Medium priority block",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert result.should_block is True
        # First executed rule (high priority) sets the block reason
        assert result.block_reason == "High priority block"

    def test_only_ok_rules_produces_no_warnings_or_blocks(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule("ok-1", {"pre_tool_use"}, result="ok"),
            make_rule("ok-2", {"pre_tool_use"}, result="ok"),
            make_rule("ok-3", {"pre_tool_use"}, result="ok"),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert result.should_block is False
        assert result.block_reason is None
        assert len(result.warnings) == 0

    def test_warn_and_block_with_terminal_stops_before_later_warnings(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "warn-before",
                {"pre_tool_use"},
                priority=RulePriority.CRITICAL,
                result="warn",
                description="Warning before block",
            ),
            make_rule(
                "terminal-block",
                {"pre_tool_use"},
                priority=RulePriority.HIGH,
                result="block",
                terminal=True,
                description="Terminal block",
            ),
            make_rule(
                "warn-after",
                {"pre_tool_use"},
                priority=RulePriority.LOW,
                result="warn",
                description="Warning after block - should not appear",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert result.should_block is True
        assert result.block_reason == "Terminal block"
        assert result.terminated_early is True
        assert len(result.warnings) == 1
        assert "Warning before block" in result.warnings
        assert "Warning after block" not in result.warnings


class TestFilteringAndExecution:
    def test_disabled_rules_not_matched_or_executed(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "disabled-rule",
                {"pre_tool_use"},
                enabled=False,
                result="block",
                description="Should not block",
            ),
            make_rule(
                "enabled-rule",
                {"pre_tool_use"},
                enabled=True,
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "enabled-rule"
        assert result.should_block is False

    def test_wrong_event_type_rules_not_executed(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "wrong-event",
                {"post_tool_use"},
                result="block",
                description="Should not block",
            ),
            make_rule(
                "correct-event",
                {"pre_tool_use"},
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "correct-event"

    def test_non_matching_conditions_filter_out_rules(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule(
                "wrong-condition",
                {"pre_tool_use"},
                condition='tool_name == "Read"',
                result="block",
            ),
            make_rule(
                "matching-condition",
                {"pre_tool_use"},
                condition='tool_name == "Bash"',
                result="ok",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "matching-condition"


class TestComplexScenarios:
    def test_realistic_security_rules_scenario(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Use regex match (=~) instead of Python 'in' operator
        rules = [
            make_rule(
                "dangerous-command-block",
                {"pre_tool_use"},
                priority=RulePriority.CRITICAL,
                condition='tool_name == "Bash" and tool_input["command"] =~ "rm -rf"',
                result="block",
                terminal=True,
                description="Blocked dangerous rm -rf command",
                actions=[make_action("log")],
            ),
            make_rule(
                "bash-audit",
                {"pre_tool_use"},
                priority=RulePriority.MEDIUM,
                condition='tool_name == "Bash"',
                result="warn",
                description="Bash command requires review",
                actions=[make_action("log")],
            ),
            make_rule(
                "all-tools-log",
                {"all"},
                priority=RulePriority.LOW,
                result="ok",
                actions=[make_action("log")],
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        # Critical terminal blocker should stop execution
        assert result.should_block is True
        assert result.block_reason == "Blocked dangerous rm -rf command"
        assert result.terminated_early is True
        # Only the critical rule should have executed
        assert len(result.rule_results) == 1
        assert result.rule_results[0].rule_id == "dangerous-command-block"

    def test_empty_rules_returns_clean_result(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = run_engine([], pre_tool_use_context)

        assert isinstance(result, ExecutionResult)
        assert len(result.rule_results) == 0
        assert result.should_block is False
        assert result.block_reason is None
        assert len(result.warnings) == 0
        assert result.terminated_early is False

    def test_all_rules_filtered_returns_clean_result(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rules = [
            make_rule("disabled", {"pre_tool_use"}, enabled=False, result="block"),
            make_rule("wrong-event", {"post_tool_use"}, result="block"),
            make_rule(
                "wrong-condition",
                {"pre_tool_use"},
                condition='tool_name == "Write"',
                result="block",
            ),
        ]

        result = run_engine(rules, pre_tool_use_context)

        assert len(result.rule_results) == 0
        assert result.should_block is False
