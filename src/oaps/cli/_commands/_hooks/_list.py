# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# ruff: noqa: D415, A002, BLE001
"""List subcommand for hooks."""

from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_error, exit_with_success
from oaps.config import (
    HookRuleConfiguration,
    RulePriority,
    find_project_root,
    load_all_hook_rules,
)
from oaps.utils import create_hooks_logger

from ._app import app
from ._formatters import (
    format_rule_detail,
    format_rule_json,
    format_rule_table,
    format_rule_yaml,
)


def _filter_rules(
    rules: list[HookRuleConfiguration],
    *,
    event: str | None = None,
    priority: str | None = None,
    enabled_only: bool = False,
) -> list[HookRuleConfiguration]:
    """Filter rules based on criteria.

    Args:
        rules: List of rules to filter.
        event: Filter by event type (e.g., "pre_tool_use").
        priority: Filter by priority level (e.g., "high").
        enabled_only: If True, only include enabled rules.

    Returns:
        Filtered list of rules.
    """
    result = rules

    if enabled_only:
        result = [r for r in result if r.enabled]

    if event:
        result = [r for r in result if event in r.events or "all" in r.events]

    if priority:
        try:
            prio = RulePriority(priority.lower())
            result = [r for r in result if r.priority == prio]
        except ValueError:
            # Invalid priority, return empty
            result = []

    return result


@app.command(name="list")
def _list(
    *,
    event: Annotated[
        str | None,
        Parameter(
            name=["--event", "-e"],
            help="Filter by event type (e.g., pre_tool_use, post_tool_use)",
        ),
    ] = None,
    priority: Annotated[
        str | None,
        Parameter(
            name=["--priority", "-p"],
            help="Filter by priority (critical, high, medium, low)",
        ),
    ] = None,
    enabled_only: Annotated[
        bool,
        Parameter(
            name="--enabled-only",
            help="Show only enabled rules",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        Parameter(
            name=["-v", "--verbose"],
            help="Show detailed rule information",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (table, json, yaml)",
        ),
    ] = OutputFormat.TABLE,
) -> None:
    """List configured hook rules

    Shows all hook rules loaded from all configuration sources.
    Rules are displayed in priority order (critical first, then high, medium, low).

    Use filters to narrow results:
      --event pre_tool_use     Show rules for specific event
      --priority high          Show rules with specific priority
      --enabled-only           Show only enabled rules

    Exit codes:
        0: Success
        1: Failed to load configuration files
    """
    logger = create_hooks_logger()

    # Resolve project root
    project_root = find_project_root()

    # Load all rules
    try:
        rules = load_all_hook_rules(project_root, logger)
    except Exception as e:
        exit_with_error(f"Loading hook rules: {e}", ExitCode.LOAD_ERROR)

    # Apply filters
    filtered = _filter_rules(
        rules,
        event=event,
        priority=priority,
        enabled_only=enabled_only,
    )

    # Handle empty results
    if not filtered:
        if format == OutputFormat.JSON:
            print('{"rules": []}')
        elif format == OutputFormat.YAML:
            print("rules: []")
        elif rules and (event or priority or enabled_only):
            print("No rules match the specified filters.")
        else:
            print("No hook rules configured.")
        exit_with_success()

    # Format output
    if format == OutputFormat.JSON:
        print(format_rule_json(filtered))
    elif format == OutputFormat.YAML:
        print(format_rule_yaml(filtered).rstrip())
    elif verbose:
        for i, rule in enumerate(filtered):
            if i > 0:
                print()
                print("-" * 40)
                print()
            print(format_rule_detail(rule))
    else:
        print(format_rule_table(filtered).rstrip())

    exit_with_success()
