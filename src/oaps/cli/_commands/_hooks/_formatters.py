# pyright: reportExplicitAny=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# ruff: noqa: TC003, PLR2004
"""Output formatting utilities for hooks commands."""

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oaps.config import HookRuleConfiguration
    from oaps.hooks._matcher import MatchedRule

# Type alias for serialized rule data
RuleData = dict[str, Any]


def rule_to_dict(rule: HookRuleConfiguration) -> RuleData:
    """Convert HookRuleConfiguration to a serializable dictionary.

    Args:
        rule: The hook rule configuration to convert.

    Returns:
        A dictionary representation suitable for JSON/YAML serialization.
    """
    return {
        "id": rule.id,
        "priority": rule.priority.value,
        "events": sorted(rule.events),
        "condition": rule.condition,
        "enabled": rule.enabled,
        "terminal": rule.terminal,
        "result": rule.result,
        "description": rule.description,
        "source_file": str(rule.source_file) if rule.source_file else None,
        "actions": [
            {k: v for k, v in action.model_dump().items() if v is not None}
            for action in rule.actions
        ],
    }


def format_rule_table(rules: list[HookRuleConfiguration]) -> str:
    """Format rules as a Markdown table.

    Args:
        rules: List of hook rule configurations to format.

    Returns:
        A formatted Markdown table string.
    """
    from pytablewriter import MarkdownTableWriter

    headers = ["ID", "Priority", "Events", "Enabled", "Source", "Description"]
    rows: list[list[str]] = []

    for rule in rules:
        events = ", ".join(sorted(rule.events)[:3])
        if len(rule.events) > 3:
            events += f" (+{len(rule.events) - 3})"

        source = rule.source_file.name if rule.source_file else "-"
        desc = rule.description or "-"
        if len(desc) > 40:
            desc = desc[:37] + "..."

        rows.append(
            [
                rule.id,
                rule.priority.value,
                events,
                "yes" if rule.enabled else "no",
                source,
                desc,
            ]
        )

    writer = MarkdownTableWriter(headers=headers, value_matrix=rows, margin=1)
    return writer.dumps()


def format_rule_json(
    rules: list[HookRuleConfiguration],
    *,
    indent: bool = True,
) -> str:
    """Format rules as JSON.

    Args:
        rules: List of hook rule configurations to format.
        indent: Whether to pretty-print with indentation.

    Returns:
        A JSON string representation.
    """
    import orjson

    data = {"rules": [rule_to_dict(rule) for rule in rules]}
    options = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(data, option=options).decode("utf-8")


def format_rule_yaml(rules: list[HookRuleConfiguration]) -> str:
    """Format rules as YAML.

    Args:
        rules: List of hook rule configurations to format.

    Returns:
        A YAML string representation.
    """
    import yaml

    data = {"rules": [rule_to_dict(rule) for rule in rules]}
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def format_rule_detail(rule: HookRuleConfiguration) -> str:
    """Format a single rule with full details.

    Args:
        rule: The hook rule configuration to format.

    Returns:
        A multi-line detailed string representation.
    """
    lines = [
        f"Rule: {rule.id}",
        f"  Priority: {rule.priority.value}",
        f"  Enabled: {rule.enabled}",
        f"  Terminal: {rule.terminal}",
        f"  Result: {rule.result}",
        f"  Events: {', '.join(sorted(rule.events))}",
        f"  Condition: {rule.condition}",
    ]

    if rule.description:
        lines.append(f"  Description: {rule.description}")

    if rule.source_file:
        lines.append(f"  Source: {rule.source_file}")

    if rule.actions:
        lines.append("  Actions:")
        for i, action in enumerate(rule.actions, 1):
            lines.append(f"    {i}. type={action.type}")
            if action.message:
                lines.append(f"       message={action.message}")
            if action.entrypoint:
                lines.append(f"       entrypoint={action.entrypoint}")
            if action.command:
                lines.append(f"       command={action.command}")

    return "\n".join(lines)


def format_source_table(sources: list[tuple[Path, int]]) -> str:
    """Format rule sources as a table.

    Args:
        sources: List of (path, rule_count) tuples.

    Returns:
        A formatted Markdown table string.
    """
    from pytablewriter import MarkdownTableWriter

    headers = ["Source", "Rules"]
    rows = [[str(path), str(count)] for path, count in sources]

    writer = MarkdownTableWriter(headers=headers, value_matrix=rows, margin=1)
    return writer.dumps()


def format_match_result(
    matched: list[MatchedRule],
    context_desc: str,
) -> str:
    """Format match results for test command output.

    Args:
        matched: List of matched rules with their match order.
        context_desc: Description of the test context.

    Returns:
        A formatted string showing match results.
    """
    lines = [
        f"Test Context: {context_desc}",
        "",
    ]

    if not matched:
        lines.append("No rules matched.")
    else:
        lines.append(f"Matched {len(matched)} rule(s):")
        lines.append("")
        for m in matched:
            lines.append(f"  {m.match_order + 1}. {m.rule.id}")
            lines.append(f"     Priority: {m.rule.priority.value}")
            lines.append(f"     Result: {m.rule.result}")
            if m.rule.description:
                lines.append(f"     Description: {m.rule.description}")
            lines.append("")

    return "\n".join(lines)


def format_validation_issues(
    issues: list[tuple[str, str, str]],
) -> str:
    """Format validation issues as human-readable text.

    Args:
        issues: List of (rule_id, issue_type, message) tuples.

    Returns:
        A formatted string showing validation issues.
    """
    if not issues:
        return "No validation issues found."

    lines = ["Validation Issues:", ""]
    for rule_id, issue_type, message in issues:
        lines.append(f"  [{issue_type}] {rule_id}: {message}")

    return "\n".join(lines)
