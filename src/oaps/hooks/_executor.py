"""Rule execution engine for hook actions.

This module provides the execution engine for running actions defined in hook
rules, aggregating results and determining overall execution outcome.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from ._action import (
    AllowAction,
    DenyAction,
    InjectAction,
    LogAction,
    ModifyAction,
    NoOpAction,
    OutputAccumulator,
    PythonAction,
    ScriptAction,
    SuggestAction,
    TransformAction,
    WarnAction,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from structlog.typing import FilteringBoundLogger

    from oaps.config import HookRuleActionConfiguration
    from oaps.hooks._context import HookContext

    from ._action import Action, PermissionAction
    from ._matcher import MatchedRule


# Permission and feedback action types that require OutputAccumulator
_PERMISSION_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "deny",
        "allow",
        "warn",
        "suggest",
        "inject",
        "log",
        "python",
        "shell",
        "modify",
        "transform",
    }
)

# Static dispatch table for basic action types (no accumulator)
# Empty since all action types now use OutputAccumulator
_ACTION_DISPATCH: dict[str, type[Action]] = {}

# Dispatch table for permission and feedback actions (require accumulator)
_PERMISSION_ACTION_DISPATCH: dict[str, type[PermissionAction]] = {
    "deny": DenyAction,
    "allow": AllowAction,
    "warn": WarnAction,
    "suggest": SuggestAction,
    "inject": InjectAction,
    "log": LogAction,
    "python": PythonAction,
    "shell": ScriptAction,
    "modify": ModifyAction,
    "transform": TransformAction,
}


@dataclass(frozen=True, slots=True)
class ActionResult:
    """Result of executing a single action.

    Attributes:
        action_type: The type of action that was executed.
        success: Whether the action completed successfully.
        error: Error message if the action failed, None otherwise.
        output: Output from the action if any, None otherwise.
    """

    action_type: str
    success: bool
    error: str | None = None
    output: str | None = None


@dataclass(frozen=True, slots=True)
class RuleExecutionResult:
    """Result of executing a rule's actions.

    Attributes:
        rule_id: The unique identifier of the executed rule.
        action_results: Tuple of ActionResult for each action executed.
        result_type: The rule's result type (block, ok, or warn).
        is_terminal: Whether this rule stops further rule processing.
    """

    rule_id: str
    action_results: tuple[ActionResult, ...]
    result_type: Literal["block", "ok", "warn"]
    is_terminal: bool


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Aggregate result from executing all matched rules.

    Attributes:
        rule_results: Tuple of RuleExecutionResult for each executed rule.
        should_block: Whether hook execution should be blocked.
        block_reason: Reason for blocking if should_block is True.
        warnings: Tuple of warning messages from rules with result="warn".
        terminated_early: Whether execution stopped due to a terminal rule.
    """

    rule_results: tuple[RuleExecutionResult, ...]
    should_block: bool
    block_reason: str | None
    warnings: tuple[str, ...]
    terminated_early: bool


def _get_action_handler(action_type: str) -> Action:
    """Get the action handler for a given action type.

    Args:
        action_type: The action type string.

    Returns:
        An Action instance for the given type.

    Note:
        Permission action types (deny, allow, warn) are not handled here.
        Use _get_permission_action_handler for those.
    """
    handler_class = _ACTION_DISPATCH.get(action_type)
    if handler_class is None:
        return NoOpAction()
    return handler_class()


def _get_permission_action_handler(action_type: str) -> PermissionAction | None:
    """Get the permission action handler for a given action type.

    Args:
        action_type: The action type string.

    Returns:
        A PermissionAction instance, or None if not a permission action type.
    """
    handler_class = _PERMISSION_ACTION_DISPATCH.get(action_type)
    if handler_class is None:
        return None
    return handler_class()


def _execute_action(
    action_config: HookRuleActionConfiguration,
    context: HookContext,
    logger: FilteringBoundLogger,
    accumulator: OutputAccumulator | None = None,
) -> ActionResult:
    """Execute a single action, catching and logging errors.

    Args:
        action_config: The action configuration to execute.
        context: The hook context.
        logger: Logger for error reporting.
        accumulator: Optional output accumulator for permission actions.

    Returns:
        ActionResult indicating success or failure.

    Raises:
        BlockHook: If a permission action (deny) blocks execution.
    """
    from oaps.exceptions import BlockHook  # noqa: PLC0415

    action_type = action_config.type

    # Debug log action execution start
    logger.debug(
        "action_executing",
        action_type=action_type,
        action_config=action_config.model_dump(exclude_none=True),
    )

    # Check if this is a permission action
    if action_type in _PERMISSION_ACTION_TYPES:
        permission_handler = _get_permission_action_handler(action_type)
        if permission_handler is not None:
            # Accumulator is required for permission actions to capture decisions
            if accumulator is None:
                logger.warning(
                    "Permission action called without accumulator",
                    action_type=action_type,
                )
                accumulator = OutputAccumulator()
            try:
                permission_handler.run(context, action_config, accumulator)
                logger.debug(
                    "action_completed",
                    action_type=action_type,
                    success=True,
                )
                return ActionResult(action_type=action_type, success=True)
            except BlockHook:
                # Re-raise BlockHook - this is expected behavior for deny
                raise
            except Exception as e:  # noqa: BLE001
                # Fail-open: log error and continue
                logger.warning(
                    "Permission action execution failed",
                    action_type=action_type,
                    error=str(e),
                )
                return ActionResult(
                    action_type=action_type,
                    success=False,
                    error=str(e),
                )

    # Handle regular actions
    handler = _get_action_handler(action_type)

    try:
        handler.run(context, action_config)
        logger.debug(
            "action_completed",
            action_type=action_type,
            success=True,
        )
        return ActionResult(action_type=action_type, success=True)
    except Exception as e:  # noqa: BLE001
        # Fail-open: log error and continue
        logger.warning(
            "Action execution failed",
            action_type=action_type,
            error=str(e),
        )
        return ActionResult(
            action_type=action_type,
            success=False,
            error=str(e),
        )


def _execute_rule(
    matched_rule: MatchedRule,
    context: HookContext,
    logger: FilteringBoundLogger,
    accumulator: OutputAccumulator | None = None,
) -> RuleExecutionResult:
    """Execute all actions for a matched rule.

    Args:
        matched_rule: The matched rule to execute.
        context: The hook context.
        logger: Logger for error reporting.
        accumulator: Optional output accumulator for permission actions.

    Returns:
        RuleExecutionResult with all action results.

    Raises:
        BlockHook: If a permission action (deny) blocks execution.
    """
    rule = matched_rule.rule
    action_results: list[ActionResult] = []

    for action_config in rule.actions:
        result = _execute_action(action_config, context, logger, accumulator)
        action_results.append(result)

    return RuleExecutionResult(
        rule_id=rule.id,
        action_results=tuple(action_results),
        result_type=rule.result,
        is_terminal=rule.terminal,
    )


def execute_rules(
    matched_rules: Sequence[MatchedRule],
    context: HookContext,
    accumulator: OutputAccumulator | None = None,
) -> ExecutionResult:
    """Execute actions for matched rules in order.

    Executes rules in the order provided (should be pre-sorted by priority).
    For each rule:
    - Executes all actions in order
    - Catches action errors and logs them (fail-open)
    - Tracks block decisions and warnings
    - Stops after executing a terminal rule

    Args:
        matched_rules: Sequence of MatchedRule to execute (pre-sorted).
        context: The HookContext for execution.
        accumulator: Optional output accumulator for permission actions.

    Returns:
        ExecutionResult with aggregate results from all executed rules.

    Raises:
        BlockHook: If a permission action (deny) blocks execution.
    """
    logger = context.hook_logger
    rule_results: list[RuleExecutionResult] = []
    warnings: list[str] = []
    should_block = False
    block_reason: str | None = None
    terminated_early = False

    for matched_rule in matched_rules:
        rule = matched_rule.rule

        # Log rule execution start
        logger.debug(
            "Executing rule",
            rule_id=rule.id,
            priority=rule.priority.value,
            match_order=matched_rule.match_order,
        )

        # Execute the rule
        rule_result = _execute_rule(matched_rule, context, logger, accumulator)
        rule_results.append(rule_result)

        # Process result type
        if rule_result.result_type == "block":
            should_block = True
            if block_reason is None:
                block_reason = rule.description or f"Blocked by rule: {rule.id}"

        elif rule_result.result_type == "warn":
            warning_msg = rule.description or f"Warning from rule: {rule.id}"
            warnings.append(warning_msg)

        # Check for terminal rule
        if rule_result.is_terminal:
            terminated_early = True
            logger.debug(
                "Terminal rule executed, stopping rule processing",
                rule_id=rule.id,
            )
            break

    result = ExecutionResult(
        rule_results=tuple(rule_results),
        should_block=should_block,
        block_reason=block_reason,
        warnings=tuple(warnings),
        terminated_early=terminated_early,
    )

    # Debug log execution summary
    logger.debug(
        "rules_execution_complete",
        rules_executed=len(rule_results),
        should_block=should_block,
        block_reason=block_reason,
        warnings_count=len(warnings),
        terminated_early=terminated_early,
    )

    return result
