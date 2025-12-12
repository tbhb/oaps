"""Rule matching for hook conditions.

This module provides functions to match hook rules against a given context,
filtering and sorting them by priority and definition order.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from oaps.config import RulePriority
from oaps.exceptions import ExpressionError

from ._expression import ExpressionEvaluator, create_function_registry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from oaps.config import HookRuleConfiguration
    from oaps.hooks._context import HookContext
    from oaps.session import Session


# Priority order mapping: lower number = higher priority
_PRIORITY_ORDER: dict[RulePriority, int] = {
    RulePriority.CRITICAL: 0,
    RulePriority.HIGH: 1,
    RulePriority.MEDIUM: 2,
    RulePriority.LOW: 3,
}


@dataclass(frozen=True, slots=True)
class MatchedRule:
    """A rule that matched the current context.

    Attributes:
        rule: The HookRuleConfiguration that matched.
        match_order: Position in the sorted sequence (0-indexed).
    """

    rule: HookRuleConfiguration
    match_order: int


def _extract_cwd(hook_input: object) -> str:
    """Extract cwd from hook_input, returning empty string if not available."""
    cwd: object = getattr(hook_input, "cwd", None)
    if cwd is not None:
        return str(cwd)
    return ""


def _matches_event(rule: HookRuleConfiguration, event_value: str) -> bool:
    """Check if rule's events match the given event value.

    Args:
        rule: The rule to check.
        event_value: The event type value (e.g., "pre_tool_use").

    Returns:
        True if the rule applies to this event.
    """
    return "all" in rule.events or event_value in rule.events


def _evaluate_condition(
    rule: HookRuleConfiguration,
    context: HookContext,
    session: Session | None,
    logger: object,
) -> bool:
    """Evaluate a rule's condition, returning False on error (fail-open).

    Args:
        rule: The rule whose condition to evaluate.
        context: The hook context.
        session: Optional session for $session_get.
        logger: Logger for error reporting.

    Returns:
        True if condition matches, False if it doesn't or on error.
    """
    cwd = _extract_cwd(context.hook_input)
    registry = create_function_registry(cwd=cwd, session=session)

    try:
        evaluator = ExpressionEvaluator.compile(rule.condition, registry)
        return evaluator.evaluate(context)
    except ExpressionError as e:
        # Fail-open: log error and skip this rule
        if hasattr(logger, "warning"):
            logger.warning(  # pyright: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
                "Rule condition evaluation failed, skipping rule",
                rule_id=rule.id,
                condition=rule.condition,
                error=str(e),
            )
        return False


def _sort_key(rule: HookRuleConfiguration, definition_order: int) -> tuple[int, int]:
    """Create sort key for rule ordering.

    Args:
        rule: The rule to create a key for.
        definition_order: Original position in the rules sequence.

    Returns:
        Tuple of (priority_order, definition_order) for sorting.
    """
    priority_order = _PRIORITY_ORDER.get(rule.priority, 2)  # Default to medium
    return (priority_order, definition_order)


def match_rules(
    rules: Sequence[HookRuleConfiguration],
    context: HookContext,
    session: Session | None = None,
) -> list[MatchedRule]:
    """Match rules against context, returning sorted by priority.

    Filters rules by:
    - enabled == True
    - event matches context.hook_event_type or rule has "all" event
    - condition evaluates to True (or is empty)

    Rules are sorted by:
    1. Priority (critical=0, high=1, medium=2, low=3)
    2. Definition order (original position in rules sequence)

    Condition evaluation errors are logged and the rule is skipped (fail-open).

    Args:
        rules: Sequence of HookRuleConfiguration to evaluate.
        context: The HookContext to match against.
        session: Optional Session for $session_get function.

    Returns:
        List of MatchedRule objects sorted by priority and definition order.
    """
    event_value = context.hook_event_type.value
    logger = context.hook_logger

    # Collect matching rules with their definition order
    matching: list[tuple[HookRuleConfiguration, int]] = []

    for definition_order, rule in enumerate(rules):
        # Filter: must be enabled
        if not rule.enabled:
            logger.debug(
                "rule_skipped_disabled",
                rule_id=rule.id,
                reason="disabled",
            )
            continue

        # Filter: must match event
        if not _matches_event(rule, event_value):
            logger.debug(
                "rule_skipped_event_mismatch",
                rule_id=rule.id,
                rule_events=list(rule.events),
                hook_event=event_value,
            )
            continue

        # Filter: condition must match (fail-open on error)
        condition_result = _evaluate_condition(rule, context, session, logger)
        logger.debug(
            "rule_condition_evaluated",
            rule_id=rule.id,
            condition=rule.condition,
            result=condition_result,
        )
        if not condition_result:
            continue

        matching.append((rule, definition_order))
        logger.debug(
            "rule_matched",
            rule_id=rule.id,
            priority=rule.priority.value,
            definition_order=definition_order,
        )

    # Sort by priority, then definition order
    matching.sort(key=lambda item: _sort_key(item[0], item[1]))

    # Create MatchedRule objects with final match_order
    return [
        MatchedRule(rule=rule, match_order=match_order)
        for match_order, (rule, _) in enumerate(matching)
    ]
