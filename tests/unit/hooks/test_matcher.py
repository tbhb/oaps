from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pytest

from oaps.config import HookRuleConfiguration, RulePriority
from oaps.enums import HookEventType
from oaps.hooks import PreToolUseInput, match_rules
from oaps.hooks._context import HookContext

if TYPE_CHECKING:
    from unittest.mock import MagicMock


@pytest.fixture
def mock_logger() -> MagicMock:
    from unittest.mock import MagicMock

    return MagicMock()


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
        actions=[],
    )


class TestEventFiltering:
    def test_rules_with_matching_event_type_pass(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"})
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1
        assert result[0].rule.id == "test-rule"

    def test_rules_with_non_matching_event_type_are_filtered_out(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"post_tool_use"})
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 0

    def test_rules_with_all_in_events_match_any_event(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"all"})
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1
        assert result[0].rule.id == "test-rule"

    def test_rules_with_multiple_events_match_if_any_event_matches(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use", "post_tool_use", "notification"})
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1

    def test_rules_with_multiple_non_matching_events_are_filtered_out(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule", {"post_tool_use", "notification", "session_start"}
        )
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 0


class TestEnabledFiltering:
    def test_disabled_rules_are_filtered_out(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, enabled=False)
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 0

    def test_enabled_rules_pass_through(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, enabled=True)
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1


class TestConditionEvaluation:
    def test_rules_with_matching_conditions_pass(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, condition='tool_name == "Bash"')
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1

    def test_rules_with_non_matching_conditions_are_filtered_out(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, condition='tool_name == "Read"')
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 0

    def test_empty_condition_always_matches(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, condition="")
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1

    def test_whitespace_condition_always_matches(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, condition="   \t  ")
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1

    def test_rules_with_invalid_conditions_are_skipped(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Invalid syntax should cause the rule to be skipped (fail-open)
        rule = make_rule("test-rule", {"pre_tool_use"}, condition="invalid !@# syntax")
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 0

    def test_invalid_condition_logs_warning(
        self, pre_tool_use_context: HookContext, mock_logger: MagicMock
    ) -> None:
        rule = make_rule("test-rule", {"pre_tool_use"}, condition="invalid !@# syntax")
        match_rules([rule], pre_tool_use_context)
        mock_logger.warning.assert_called()  # pyright: ignore[reportAny]

    def test_complex_condition_evaluation(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            condition='tool_name == "Bash" and permission_mode == "default"',
        )
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1


class TestPrioritySorting:
    def test_critical_rules_come_before_high(
        self, pre_tool_use_context: HookContext
    ) -> None:
        high_rule = make_rule("high-rule", {"pre_tool_use"}, priority=RulePriority.HIGH)
        critical_rule = make_rule(
            "critical-rule", {"pre_tool_use"}, priority=RulePriority.CRITICAL
        )
        # Define high before critical to test sorting
        result = match_rules([high_rule, critical_rule], pre_tool_use_context)
        assert len(result) == 2
        assert result[0].rule.id == "critical-rule"
        assert result[1].rule.id == "high-rule"

    def test_high_rules_come_before_medium(
        self, pre_tool_use_context: HookContext
    ) -> None:
        medium_rule = make_rule(
            "medium-rule", {"pre_tool_use"}, priority=RulePriority.MEDIUM
        )
        high_rule = make_rule("high-rule", {"pre_tool_use"}, priority=RulePriority.HIGH)
        result = match_rules([medium_rule, high_rule], pre_tool_use_context)
        assert len(result) == 2
        assert result[0].rule.id == "high-rule"
        assert result[1].rule.id == "medium-rule"

    def test_medium_rules_come_before_low(
        self, pre_tool_use_context: HookContext
    ) -> None:
        low_rule = make_rule("low-rule", {"pre_tool_use"}, priority=RulePriority.LOW)
        medium_rule = make_rule(
            "medium-rule", {"pre_tool_use"}, priority=RulePriority.MEDIUM
        )
        result = match_rules([low_rule, medium_rule], pre_tool_use_context)
        assert len(result) == 2
        assert result[0].rule.id == "medium-rule"
        assert result[1].rule.id == "low-rule"

    def test_full_priority_ordering(self, pre_tool_use_context: HookContext) -> None:
        low_rule = make_rule("low", {"pre_tool_use"}, priority=RulePriority.LOW)
        medium_rule = make_rule(
            "medium", {"pre_tool_use"}, priority=RulePriority.MEDIUM
        )
        high_rule = make_rule("high", {"pre_tool_use"}, priority=RulePriority.HIGH)
        critical_rule = make_rule(
            "critical", {"pre_tool_use"}, priority=RulePriority.CRITICAL
        )
        # Provide in reverse order
        rules = [low_rule, medium_rule, high_rule, critical_rule]
        result = match_rules(rules, pre_tool_use_context)
        assert len(result) == 4
        assert result[0].rule.id == "critical"
        assert result[1].rule.id == "high"
        assert result[2].rule.id == "medium"
        assert result[3].rule.id == "low"

    def test_definition_order_preserved_within_same_priority(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule_a = make_rule("rule-a", {"pre_tool_use"}, priority=RulePriority.MEDIUM)
        rule_b = make_rule("rule-b", {"pre_tool_use"}, priority=RulePriority.MEDIUM)
        rule_c = make_rule("rule-c", {"pre_tool_use"}, priority=RulePriority.MEDIUM)
        result = match_rules([rule_a, rule_b, rule_c], pre_tool_use_context)
        assert len(result) == 3
        assert result[0].rule.id == "rule-a"
        assert result[1].rule.id == "rule-b"
        assert result[2].rule.id == "rule-c"

    def test_definition_order_preserved_with_mixed_priorities(
        self, pre_tool_use_context: HookContext
    ) -> None:
        # Two high priority rules defined first, then two medium
        high_1 = make_rule("high-1", {"pre_tool_use"}, priority=RulePriority.HIGH)
        high_2 = make_rule("high-2", {"pre_tool_use"}, priority=RulePriority.HIGH)
        medium_1 = make_rule("medium-1", {"pre_tool_use"}, priority=RulePriority.MEDIUM)
        medium_2 = make_rule("medium-2", {"pre_tool_use"}, priority=RulePriority.MEDIUM)
        result = match_rules([medium_1, high_1, medium_2, high_2], pre_tool_use_context)
        assert len(result) == 4
        # High priority rules first, in definition order (high_1 then high_2)
        assert result[0].rule.id == "high-1"
        assert result[1].rule.id == "high-2"
        # Medium priority rules second, in definition order
        assert result[2].rule.id == "medium-1"
        assert result[3].rule.id == "medium-2"


class TestMatchedRuleStructure:
    def test_rule_field_contains_original_configuration(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule(
            "test-rule",
            {"pre_tool_use"},
            description="A test rule",
            priority=RulePriority.HIGH,
        )
        result = match_rules([rule], pre_tool_use_context)
        assert len(result) == 1
        assert result[0].rule is rule

    def test_match_order_reflects_position_in_sorted_result(
        self, pre_tool_use_context: HookContext
    ) -> None:
        low_rule = make_rule("low", {"pre_tool_use"}, priority=RulePriority.LOW)
        high_rule = make_rule("high", {"pre_tool_use"}, priority=RulePriority.HIGH)
        medium_rule = make_rule(
            "medium", {"pre_tool_use"}, priority=RulePriority.MEDIUM
        )
        result = match_rules([low_rule, high_rule, medium_rule], pre_tool_use_context)
        assert len(result) == 3
        # After sorting: high, medium, low
        assert result[0].match_order == 0
        assert result[0].rule.id == "high"
        assert result[1].match_order == 1
        assert result[1].rule.id == "medium"
        assert result[2].match_order == 2
        assert result[2].rule.id == "low"


class TestEmptyAndEdgeCases:
    def test_empty_rules_returns_empty_list(
        self, pre_tool_use_context: HookContext
    ) -> None:
        result = match_rules([], pre_tool_use_context)
        assert result == []

    def test_all_rules_filtered_out_returns_empty_list(
        self, pre_tool_use_context: HookContext
    ) -> None:
        rule = make_rule("test-rule", {"post_tool_use"}, enabled=False)
        result = match_rules([rule], pre_tool_use_context)
        assert result == []

    def test_multiple_filters_combined(self, pre_tool_use_context: HookContext) -> None:
        # Rule with matching event but disabled
        disabled_rule = make_rule("disabled", {"pre_tool_use"}, enabled=False)
        # Rule with non-matching event but enabled
        wrong_event_rule = make_rule("wrong-event", {"post_tool_use"}, enabled=True)
        # Rule with non-matching condition
        wrong_condition_rule = make_rule(
            "wrong-condition",
            {"pre_tool_use"},
            condition='tool_name == "Read"',
        )
        # Rule that should match
        matching_rule = make_rule(
            "matching",
            {"pre_tool_use"},
            condition='tool_name == "Bash"',
            enabled=True,
        )
        rules = [disabled_rule, wrong_event_rule, wrong_condition_rule, matching_rule]
        result = match_rules(rules, pre_tool_use_context)
        assert len(result) == 1
        assert result[0].rule.id == "matching"
