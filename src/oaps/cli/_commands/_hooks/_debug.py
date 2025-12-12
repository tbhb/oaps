# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportExplicitAny=false, reportAny=false, reportPrivateUsage=false
# ruff: noqa: D415, BLE001, PLR0912, PLR0915, PLR2004, TC003, TRY300
"""Debug subcommand for hooks."""

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from cyclopts import Parameter

from oaps.config import (
    HookRuleConfiguration,
    find_project_root,
    load_all_hook_rules,
)
from oaps.enums import HookEventType
from oaps.exceptions import ExpressionError
from oaps.hooks._context import HookContext
from oaps.hooks._expression import (
    ExpressionEvaluator,
    adapt_context,
    create_function_registry,
)
from oaps.hooks._inputs import HOOK_EVENT_TYPE_TO_MODEL
from oaps.utils import create_hooks_logger, create_session_logger, get_oaps_dir

from ._app import app
from ._exit_codes import EXIT_INPUT_ERROR, EXIT_LOAD_ERROR, EXIT_NOT_FOUND, EXIT_SUCCESS
from ._formatters import format_rule_detail
from ._test import _create_minimal_input, _parse_event_type, _read_input

if TYPE_CHECKING:
    from oaps.hooks._inputs import HookInputT


def _validate_expression_verbose(expression: str) -> tuple[bool, str]:
    """Validate expression and return detailed result.

    Args:
        expression: The expression to validate.

    Returns:
        Tuple of (is_valid, message).
    """
    if not expression.strip():
        return True, "Empty expression (always matches)"

    registry = create_function_registry(cwd=".")

    try:
        ExpressionEvaluator.compile(expression, registry)
        return True, "Valid expression"
    except ExpressionError as e:
        return False, f"Invalid: {e}"


def _evaluate_expression_verbose(
    expression: str,
    context: HookContext,
) -> tuple[bool, str, dict[str, Any]]:
    """Evaluate expression and return detailed result.

    Args:
        expression: The expression to evaluate.
        context: The hook context.

    Returns:
        Tuple of (matches, message, context_dict).
    """
    context_dict = adapt_context(context)

    if not expression.strip():
        return True, "Empty expression (always matches)", context_dict

    cwd_attr: object = getattr(context.hook_input, "cwd", None)
    cwd = str(cwd_attr) if cwd_attr is not None else "."
    registry = create_function_registry(cwd=cwd)

    try:
        evaluator = ExpressionEvaluator.compile(expression, registry)
        result = evaluator.evaluate(context)
        return result, f"Expression evaluated to: {result}", context_dict
    except ExpressionError as e:
        return False, f"Evaluation failed: {e}", context_dict


def _find_rule(
    rules: list[HookRuleConfiguration],
    rule_id: str,
) -> HookRuleConfiguration | None:
    """Find a rule by ID.

    Args:
        rules: List of rules to search.
        rule_id: The rule ID to find.

    Returns:
        The matching rule, or None if not found.
    """
    for rule in rules:
        if rule.id == rule_id:
            return rule
    return None


def _build_context(
    event_type: HookEventType,
    hook_input: HookInputT,
) -> HookContext:
    """Build a HookContext for testing.

    Args:
        event_type: The hook event type.
        hook_input: The validated hook input.

    Returns:
        A HookContext suitable for rule matching.
    """
    session_id = str(hook_input.session_id)
    hook_logger = create_hooks_logger()
    session_logger = create_session_logger(session_id)
    oaps_dir = get_oaps_dir()
    oaps_state_file = oaps_dir / "state.db"

    return HookContext(
        hook_event_type=event_type,
        hook_input=hook_input,
        claude_session_id=session_id,
        oaps_dir=oaps_dir,
        oaps_state_file=oaps_state_file,
        hook_logger=hook_logger,
        session_logger=session_logger,
        git=None,
    )


@app.command(name="debug")
def _debug(
    rule: Annotated[
        str,
        Parameter(
            help="Rule ID to debug",
        ),
    ],
    /,
    *,
    event: Annotated[
        str | None,
        Parameter(
            name=["--event", "-e"],
            help="Event type to simulate for evaluation (e.g., pre_tool_use)",
        ),
    ] = None,
    input_file: Annotated[
        Path | None,
        Parameter(
            name=["--input", "-i"],
            help="JSON file with hook input for evaluation",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(
            name=["-v", "--verbose"],
            help="Show additional details including context variables",
        ),
    ] = False,
) -> None:
    """Debug a specific hook rule

    Shows detailed information about a rule including:
    - Full rule configuration
    - Condition expression syntax validation
    - Event matching (if --event specified)
    - Condition evaluation (if --event and --input specified)

    Examples:
      # Show rule details
      oaps hooks debug my-rule-id

      # Debug with simulated event
      oaps hooks debug my-rule-id --event pre_tool_use

      # Debug with custom input
      oaps hooks debug my-rule-id --event pre_tool_use --input test.json

    Exit codes:
        0: Debug completed successfully
        1: Failed to load configuration files
        3: Rule ID not found
        4: Invalid event type or input
    """
    logger = create_hooks_logger()

    # Resolve project root
    project_root = find_project_root()

    # Load all rules
    try:
        rules = load_all_hook_rules(project_root, logger)
    except Exception as e:
        print(f"Error loading hook rules: {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    # Find the rule
    target_rule = _find_rule(rules, rule)
    if target_rule is None:
        print(f"Error: Rule '{rule}' not found")
        print()
        print("Available rules:")
        for r in rules[:10]:
            print(f"  - {r.id}")
        if len(rules) > 10:
            print(f"  ... and {len(rules) - 10} more")
        raise SystemExit(EXIT_NOT_FOUND)

    # Print rule details
    print("=" * 60)
    print("RULE DETAILS")
    print("=" * 60)
    print()
    print(format_rule_detail(target_rule))
    print()

    # Validate expression syntax
    print("=" * 60)
    print("EXPRESSION VALIDATION")
    print("=" * 60)
    print()
    is_valid, validation_msg = _validate_expression_verbose(target_rule.condition)
    status = "OK" if is_valid else "ERROR"
    print(f"Status: {status}")
    print(f"Message: {validation_msg}")
    print()

    # If event specified, test event matching
    if event:
        event_type = _parse_event_type(event)
        if event_type is None:
            valid_events = ", ".join(e.value for e in HookEventType)
            print(f"Error: Invalid event type '{event}'. Valid types: {valid_events}")
            raise SystemExit(EXIT_INPUT_ERROR)

        print("=" * 60)
        print("EVENT MATCHING")
        print("=" * 60)
        print()
        print(f"Testing event: {event}")
        print(f"Rule events: {', '.join(sorted(target_rule.events))}")

        matches_event = event in target_rule.events or "all" in target_rule.events
        match_result = "MATCHES" if matches_event else "NO MATCH"
        print(f"Result: {match_result}")
        print()

        # If input also specified, evaluate condition
        input_json = _read_input(input_file)
        model_class = HOOK_EVENT_TYPE_TO_MODEL.get(event_type)

        if model_class is None:
            print(f"Error: No input model for event type '{event}'")
            raise SystemExit(EXIT_INPUT_ERROR)

        # Parse or create input
        if input_json:
            try:
                hook_input = model_class.model_validate_json(input_json)
            except Exception as e:
                print(f"Error parsing input JSON: {e}")
                raise SystemExit(EXIT_INPUT_ERROR) from None
        else:
            # Create minimal input
            minimal = _create_minimal_input(event_type)
            try:
                hook_input = model_class.model_validate(minimal)
            except Exception as e:
                print(f"Error creating minimal input: {e}")
                raise SystemExit(EXIT_INPUT_ERROR) from None

        # Build context and evaluate
        context = _build_context(event_type, hook_input)

        print("=" * 60)
        print("CONDITION EVALUATION")
        print("=" * 60)
        print()

        if not is_valid:
            print("Skipped: Expression has syntax errors")
        else:
            _, eval_msg, context_dict = _evaluate_expression_verbose(
                target_rule.condition,
                context,
            )
            print(f"Condition: {target_rule.condition}")
            print(f"Result: {eval_msg}")

            if verbose:
                print()
                print("Context variables available:")
                for key, value in sorted(context_dict.items()):
                    val_str = str(value)
                    if len(val_str) > 60:
                        val_str = val_str[:57] + "..."
                    print(f"  {key}: {val_str}")
        print()

    # Final summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"Rule ID: {target_rule.id}")
    print(f"Enabled: {target_rule.enabled}")
    print(f"Priority: {target_rule.priority.value}")
    print(f"Expression Valid: {is_valid}")
    if event:
        event_matches = event in target_rule.events or "all" in target_rule.events
        print(f"Matches Event '{event}': {event_matches}")

    raise SystemExit(EXIT_SUCCESS)
