# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportUnusedParameter=false
# ruff: noqa: D415, A002, ARG001, BLE001, PLR0912, TC003, TRY300
"""Validate subcommand for hooks."""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_error, exit_with_success
from oaps.config import (
    HookRuleConfiguration,
    find_project_root,
    load_all_hook_rules,
)
from oaps.exceptions import ExpressionError
from oaps.utils import create_hooks_logger

from ._app import app
from ._formatters import format_validation_issues


def _validate_expression(expression: str, rule_id: str) -> str | None:
    """Validate a condition expression syntax without evaluation.

    Args:
        expression: The expression string to validate.
        rule_id: The rule ID for error messages.

    Returns:
        Error message if invalid, None if valid.
    """
    from oaps.hooks._expression import ExpressionEvaluator, create_function_registry

    # Empty expressions are valid (always match)
    if not expression.strip():
        return None

    # Create a minimal function registry for syntax validation
    registry = create_function_registry(cwd=".")

    try:
        ExpressionEvaluator.compile(expression, registry)
        return None
    except ExpressionError as e:
        return str(e)


def _collect_validation_issues(
    rules: list[HookRuleConfiguration],
) -> list[tuple[str, str, str]]:
    """Collect validation issues from rules.

    Args:
        rules: List of hook rule configurations to validate.

    Returns:
        List of (rule_id, issue_type, message) tuples.
    """
    issues: list[tuple[str, str, str]] = []

    for rule in rules:
        # Validate condition expression
        expr_error = _validate_expression(rule.condition, rule.id)
        if expr_error:
            issues.append((rule.id, "EXPRESSION", expr_error))

        # Validate actions have required fields based on type
        for i, action in enumerate(rule.actions):
            action_id = f"{rule.id}:action[{i}]"

            # Check execution actions have an execution field
            is_exec_action = action.type in ("python", "shell")
            has_exec_field = any([action.entrypoint, action.command, action.script])
            if is_exec_action and not has_exec_field:
                msg = f"'{action.type}' requires entrypoint, command, or script"
                issues.append((action_id, "ACTION", msg))

            # Check permission actions have a message
            if action.type in ("deny", "warn", "suggest") and not action.message:
                issues.append(
                    (
                        action_id,
                        "WARNING",
                        f"Action type '{action.type}' should have a message",
                    )
                )

    return issues


@app.command(name="validate")
def _validate(
    *,
    config_file: Annotated[
        Path | None,
        Parameter(
            name=["--config", "-c"],
            help="Specific config file to validate (validates all sources if omitted)",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(help="Show detailed validation output"),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Validate hook rule configurations

    Validates all hook rules from all configuration sources, checking:
    - TOML syntax errors
    - Pydantic schema validation
    - Condition expression syntax

    Exit codes:
        0: All rules valid
        1: Failed to load configuration files
        2: Validation errors found
    """
    logger = create_hooks_logger()

    # Resolve project root
    project_root = find_project_root()

    # Load all rules - the loader already validates via Pydantic
    try:
        rules = load_all_hook_rules(project_root, logger)
    except Exception as e:
        exit_with_error(f"Loading hook rules: {e}", ExitCode.LOAD_ERROR)

    if not rules:
        if format == OutputFormat.JSON:
            print('{"valid": true, "rules": 0, "issues": []}')
        else:
            print("No hook rules found.")
        exit_with_success()

    # If specific file requested, filter to rules from that file
    if config_file:
        config_path = config_file.resolve()
        rules = [r for r in rules if r.source_file and r.source_file == config_path]
        if not rules:
            exit_with_error(f"No rules found in {config_file}", ExitCode.LOAD_ERROR)

    # Collect validation issues
    issues = _collect_validation_issues(rules)

    # Separate errors from warnings
    errors = [i for i in issues if i[1] != "WARNING"]
    warnings = [i for i in issues if i[1] == "WARNING"]

    # Format output
    if format == OutputFormat.JSON:
        import orjson

        data = {
            "valid": len(errors) == 0,
            "rules": len(rules),
            "errors": [{"rule_id": r, "type": t, "message": m} for r, t, m in errors],
            "warnings": [
                {"rule_id": r, "type": t, "message": m} for r, t, m in warnings
            ],
        }
        print(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        print(f"Validating {len(rules)} hook rule(s)...")
        print()

        if errors:
            print("ERRORS:")
            print(format_validation_issues(errors))
            print()

        if warnings and verbose:
            print("WARNINGS:")
            print(format_validation_issues(warnings))
            print()

        if errors:
            print(f"Validation FAILED: {len(errors)} error(s)")
        else:
            print("Validation OK")

        if verbose:
            print()
            print("Validated rules:")
            for rule in rules:
                source = rule.source_file.name if rule.source_file else "unknown"
                print(f"  - {rule.id} ({source})")

    # Exit with appropriate code
    if errors:
        raise SystemExit(ExitCode.VALIDATION_ERROR)
    exit_with_success()
