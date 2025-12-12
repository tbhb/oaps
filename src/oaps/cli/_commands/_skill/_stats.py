# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false
# ruff: noqa: A002, PLR0912
"""Stats subcommand for skills - analyze skill usage from hook log."""

from dataclasses import dataclass
from typing import Annotated

import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.table import Table

from oaps.cli._commands._context import OutputFormat
from oaps.cli._shared import (
    count_unique_sessions,
    get_time_range,
    normalize_session_ids,
    parse_log_to_dataframe,
)
from oaps.utils import get_oaps_hooks_log_file

from ._app import app

# Exit codes (matching hooks stats pattern)
_EXIT_SUCCESS: int = 0
_EXIT_LOAD_ERROR: int = 1

# Accept rate thresholds for color coding
_ACCEPT_RATE_GOOD = 0.5
_ACCEPT_RATE_FAIR = 0.25

# Known skill rule IDs from skills.toml - used to identify skill suggestions
# Rule IDs can have suffixes like -prompt or -file that map to the same skill
# NOTE: Consider discovering these dynamically from skills.toml in the future
_SKILL_RULE_IDS = [
    "skill-developer",
    "agent-developer",
    "command-developer",
    "python-practices-prompt",
    "python-practices-file",
    "spec-writing-prompt",
    "spec-writing-file",
]


@dataclass(frozen=True, slots=True)
class SkillStats:
    """Statistics derived from skill usage log analysis.

    Attributes:
        total_suggestions: Total number of skill suggestions from rules_matched events.
        total_invocations: Total number of skill invocations via Skill tool.
        total_sessions: Number of unique sessions in analyzed data.
        suggestions_by_skill: Count of suggestions per canonical skill name.
        invocations_by_skill: Count of invocations per skill name.
        suggestions_by_rule: Count of suggestions per rule ID.
        accept_rate: Overall accept rate (invocations / suggestions), capped at 1.0.
        accept_rate_by_skill: Accept rate per canonical skill name.
        avg_time_to_invoke_seconds: Average seconds between suggestion and invocation.
        top_suggested_skills: Top skills by suggestion count.
        top_invoked_skills: Top skills by invocation count.
        sessions_with_suggestions: Number of sessions with at least one suggestion.
        sessions_with_invocations: Number of sessions with at least one invocation.
        time_range_start: Earliest timestamp in the log.
        time_range_end: Latest timestamp in the log.
    """

    total_suggestions: int
    total_invocations: int
    total_sessions: int
    suggestions_by_skill: dict[str, int]
    invocations_by_skill: dict[str, int]
    suggestions_by_rule: dict[str, int]
    accept_rate: float
    accept_rate_by_skill: dict[str, float]
    avg_time_to_invoke_seconds: float | None
    top_suggested_skills: list[tuple[str, int]]
    top_invoked_skills: list[tuple[str, int]]
    sessions_with_suggestions: int
    sessions_with_invocations: int
    time_range_start: str | None
    time_range_end: str | None


def _rule_id_to_skill_name(rule_id: str) -> str:
    """Convert a rule ID to a canonical skill name.

    Strips -prompt or -file suffixes from rule IDs to get the canonical skill name.

    Args:
        rule_id: The rule ID (e.g., "python-practices-prompt").

    Returns:
        Canonical skill name (e.g., "python-practices").
    """
    for suffix in ("-prompt", "-file"):
        if rule_id.endswith(suffix):
            return rule_id[: -len(suffix)]
    return rule_id


def _extract_skill_suggestions(
    df: pl.DataFrame,
) -> tuple[dict[str, int], dict[str, int]]:
    """Extract skill suggestions from rules_matched events.

    Looks for rules_matched events and extracts rule_ids that match known
    skill activation rules.

    Args:
        df: DataFrame with parsed hook log entries.

    Returns:
        Tuple of (suggestions_by_skill, suggestions_by_rule).
    """
    suggestions_by_skill: dict[str, int] = {}
    suggestions_by_rule: dict[str, int] = {}

    if "event" not in df.columns or "rule_ids" not in df.columns:
        return suggestions_by_skill, suggestions_by_rule

    # Filter to rules_matched events with rule_ids
    matched_df = df.filter(
        (pl.col("event") == "rules_matched") & pl.col("rule_ids").is_not_null()
    )

    if matched_df.height == 0:
        return suggestions_by_skill, suggestions_by_rule

    # Extract rule_ids and count skill suggestions
    for row in matched_df.to_dicts():
        rule_ids_raw = row.get("rule_ids")
        if not rule_ids_raw or not isinstance(rule_ids_raw, list):
            continue

        # Cast to list of strings (filter non-strings)
        rule_ids_list = [item for item in rule_ids_raw if isinstance(item, str)]

        for rule_id in rule_ids_list:
            # Check if this is a skill-related rule
            if rule_id in _SKILL_RULE_IDS:
                # Count by rule ID
                suggestions_by_rule[rule_id] = suggestions_by_rule.get(rule_id, 0) + 1
                # Count by canonical skill name
                skill_name = _rule_id_to_skill_name(rule_id)
                suggestions_by_skill[skill_name] = (
                    suggestions_by_skill.get(skill_name, 0) + 1
                )

    return suggestions_by_skill, suggestions_by_rule


def _extract_skill_invocations(df: pl.DataFrame) -> dict[str, int]:
    """Extract skill invocations from hook_input events.

    Looks for hook_input events where tool_name == "Skill" and extracts
    the skill name from tool_input.skill.

    Args:
        df: DataFrame with parsed hook log entries.

    Returns:
        Dictionary mapping skill names to invocation counts.
    """
    invocations_by_skill: dict[str, int] = {}

    if "event" not in df.columns or "input" not in df.columns:
        return invocations_by_skill

    # Filter to hook_input events
    hook_input_df = df.filter(
        (pl.col("event") == "hook_input") & pl.col("input").is_not_null()
    )

    if hook_input_df.height == 0:
        return invocations_by_skill

    # Try to extract tool_name and skill from input struct
    try:
        # Extract fields from input struct
        hook_input_df = hook_input_df.with_columns(
            [
                pl.col("input")
                .struct.field("hook_event_name")
                .alias("hook_event_name"),
                pl.col("input").struct.field("tool_name").alias("tool_name"),
                pl.col("input").struct.field("tool_input").alias("tool_input"),
            ]
        )

        # Filter to PostToolUse events with Skill tool
        skill_df = hook_input_df.filter(
            (pl.col("hook_event_name") == "PostToolUse")
            & (pl.col("tool_name") == "Skill")
            & pl.col("tool_input").is_not_null()
        )

        if skill_df.height == 0:
            return invocations_by_skill

        # Extract skill name from tool_input
        skill_df = skill_df.with_columns(
            pl.col("tool_input").struct.field("skill").alias("skill_name")
        )

        # Filter to valid skill names and count
        skill_df = skill_df.filter(pl.col("skill_name").is_not_null())

        for row in skill_df.iter_rows(named=True):
            skill_name = row.get("skill_name")
            if skill_name and isinstance(skill_name, str):
                invocations_by_skill[skill_name] = (
                    invocations_by_skill.get(skill_name, 0) + 1
                )

    except pl.exceptions.StructFieldNotFoundError:
        # Schema doesn't have expected structure
        pass

    return invocations_by_skill


def _count_sessions_with_activity(
    df: pl.DataFrame, event_type: str, filter_column: str | None = None
) -> int:
    """Count unique sessions with specific activity.

    Args:
        df: DataFrame with parsed hook log entries.
        event_type: The event type to filter for.
        filter_column: Optional column that must be non-null.

    Returns:
        Count of unique sessions with the specified activity.
    """
    if "session_id" not in df.columns or "event" not in df.columns:
        return 0

    filtered = df.filter(pl.col("event") == event_type)
    if filter_column and filter_column in df.columns:
        filtered = filtered.filter(pl.col(filter_column).is_not_null())

    if filtered.height == 0:
        return 0

    normalized = normalize_session_ids(filtered)
    return normalized.select("session_id_normalized").n_unique()


def _compute_skill_stats(df: pl.DataFrame) -> SkillStats:
    """Compute skill statistics from the parsed log DataFrame.

    Args:
        df: DataFrame with parsed hook log entries.

    Returns:
        SkillStats with computed statistics.
    """
    # Extract suggestions and invocations
    suggestions_by_skill, suggestions_by_rule = _extract_skill_suggestions(df)
    invocations_by_skill = _extract_skill_invocations(df)

    # Calculate totals
    total_suggestions = sum(suggestions_by_skill.values())
    total_invocations = sum(invocations_by_skill.values())

    # Count unique sessions
    total_sessions = count_unique_sessions(df)

    # Count sessions with suggestions/invocations
    sessions_with_suggestions = _count_sessions_with_activity(
        df, "rules_matched", "rule_ids"
    )
    sessions_with_invocations = _count_sessions_with_activity(df, "hook_input", "input")

    # Calculate accept rate (capped at 1.0)
    accept_rate = 0.0
    if total_suggestions > 0:
        accept_rate = min(1.0, total_invocations / total_suggestions)

    # Calculate per-skill accept rate
    accept_rate_by_skill: dict[str, float] = {}
    for skill_name, suggestion_count in suggestions_by_skill.items():
        if suggestion_count > 0:
            invocation_count = invocations_by_skill.get(skill_name, 0)
            accept_rate_by_skill[skill_name] = min(
                1.0, invocation_count / suggestion_count
            )

    # Time to invoke calculation is complex - requires matching suggestions to
    # invocations in same session. For now, return None (not implemented).
    avg_time_to_invoke_seconds: float | None = None

    # Top suggested/invoked skills
    top_suggested = sorted(
        suggestions_by_skill.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_invoked = sorted(
        invocations_by_skill.items(), key=lambda x: x[1], reverse=True
    )[:10]

    # Time range
    time_range_start, time_range_end = get_time_range(df)

    return SkillStats(
        total_suggestions=total_suggestions,
        total_invocations=total_invocations,
        total_sessions=total_sessions,
        suggestions_by_skill=suggestions_by_skill,
        invocations_by_skill=invocations_by_skill,
        suggestions_by_rule=suggestions_by_rule,
        accept_rate=accept_rate,
        accept_rate_by_skill=accept_rate_by_skill,
        avg_time_to_invoke_seconds=avg_time_to_invoke_seconds,
        top_suggested_skills=top_suggested,
        top_invoked_skills=top_invoked,
        sessions_with_suggestions=sessions_with_suggestions,
        sessions_with_invocations=sessions_with_invocations,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
    )


def _render_skill_stats_rich(stats: SkillStats, console: Console) -> None:
    """Render skill statistics using Rich for beautiful terminal output.

    Args:
        stats: Computed skill statistics.
        console: Rich console for output.
    """
    console.print()
    console.print("[bold blue]Skill Statistics[/bold blue]")
    console.print()

    # Single consolidated table for all stats
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Category", width=24)
    table.add_column("Value", justify="right")

    # Time range
    if stats.time_range_start and stats.time_range_end:
        table.add_row("Time Range", stats.time_range_start)
        table.add_row("", f"→ {stats.time_range_end}")
        table.add_row("", "")

    # Overview
    table.add_row("[bold cyan]Overview[/bold cyan]", "")
    table.add_row("  Total Suggestions", f"{stats.total_suggestions:,}")
    table.add_row("  Total Invocations", f"{stats.total_invocations:,}")
    table.add_row("  Sessions Analyzed", f"{stats.total_sessions:,}")
    table.add_row("  With Suggestions", f"{stats.sessions_with_suggestions:,}")
    table.add_row("  With Invocations", f"{stats.sessions_with_invocations:,}")
    table.add_row("  Accept Rate", f"{stats.accept_rate:.1%}")
    if stats.avg_time_to_invoke_seconds is not None:
        avg_time = stats.avg_time_to_invoke_seconds
        table.add_row("  Avg Time to Invoke", f"{avg_time:.1f}s")
    table.add_row("", "")

    # Top suggested skills
    if stats.top_suggested_skills:
        table.add_row("[bold cyan]Top Suggested Skills[/bold cyan]", "")
        for skill_name, count in stats.top_suggested_skills:
            table.add_row(f"  {skill_name}", f"{count:,}")
        table.add_row("", "")

    # Top invoked skills
    if stats.top_invoked_skills:
        table.add_row("[bold cyan]Top Invoked Skills[/bold cyan]", "")
        for skill_name, count in stats.top_invoked_skills:
            table.add_row(f"  {skill_name}", f"[green]{count:,}[/green]")
        table.add_row("", "")

    # Suggestions by rule
    if stats.suggestions_by_rule:
        table.add_row("[bold cyan]Suggestions by Rule[/bold cyan]", "")
        sorted_rules = sorted(
            stats.suggestions_by_rule.items(), key=lambda x: x[1], reverse=True
        )
        for rule_id, count in sorted_rules:
            table.add_row(f"  {rule_id}", f"{count:,}")
        table.add_row("", "")

    # Accept rate by skill
    if stats.accept_rate_by_skill:
        table.add_row("[bold cyan]Accept Rate by Skill[/bold cyan]", "")
        sorted_rates = sorted(
            stats.accept_rate_by_skill.items(), key=lambda x: x[1], reverse=True
        )
        for skill_name, rate in sorted_rates:
            if rate >= _ACCEPT_RATE_GOOD:
                color = "green"
            elif rate >= _ACCEPT_RATE_FAIR:
                color = "yellow"
            else:
                color = "red"
            table.add_row(f"  {skill_name}", f"[{color}]{rate:.1%}[/{color}]")

    console.print(table)
    console.print()


def _format_skill_stats_json(stats: SkillStats) -> str:
    """Format skill statistics as JSON.

    Args:
        stats: Computed skill statistics.

    Returns:
        JSON string output.
    """
    import orjson

    data = {
        "time_range": {
            "start": stats.time_range_start,
            "end": stats.time_range_end,
        },
        "overview": {
            "total_suggestions": stats.total_suggestions,
            "total_invocations": stats.total_invocations,
            "total_sessions": stats.total_sessions,
            "sessions_with_suggestions": stats.sessions_with_suggestions,
            "sessions_with_invocations": stats.sessions_with_invocations,
            "accept_rate": round(stats.accept_rate, 4),
            "avg_time_to_invoke_seconds": stats.avg_time_to_invoke_seconds,
        },
        "suggestions_by_skill": stats.suggestions_by_skill,
        "invocations_by_skill": stats.invocations_by_skill,
        "suggestions_by_rule": stats.suggestions_by_rule,
        "accept_rate_by_skill": {
            k: round(v, 4) for k, v in stats.accept_rate_by_skill.items()
        },
        "top_suggested_skills": [
            {"skill": name, "count": count}
            for name, count in stats.top_suggested_skills
        ],
        "top_invoked_skills": [
            {"skill": name, "count": count} for name, count in stats.top_invoked_skills
        ],
    }

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.command(name="stats")
def _stats(
    *,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
    session_id: Annotated[
        str | None,
        Parameter(
            name=["--session", "-s"],
            help="Filter statistics to a specific session ID",
        ),
    ] = None,
) -> None:
    """Analyze hook log and display skill usage statistics.

    Uses Polars to efficiently analyze the JSONL hook log file and provides:
    - Skill suggestion counts from rules_matched events
    - Skill invocation counts from Skill tool usage
    - Accept rate (invocations / suggestions)
    - Breakdown by skill and rule ID
    - Session analysis

    Examples:
        oaps skill stats              # Show all statistics
        oaps skill stats -f json      # Output as JSON
        oaps skill stats -s abc123    # Stats for specific session

    Exit codes:
        0: Statistics displayed successfully
        1: Failed to load or parse log file
    """
    console = Console()
    log_path = get_oaps_hooks_log_file()

    if not log_path.exists():
        console.print(f"[yellow]Hook log file not found:[/yellow] {log_path}")
        console.print("No hook executions have been recorded yet.")
        raise SystemExit(_EXIT_SUCCESS)

    try:
        df = parse_log_to_dataframe(str(log_path))
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing hook log:[/red] {e}")
        raise SystemExit(_EXIT_LOAD_ERROR) from None

    if df.height == 0:
        console.print("[yellow]Hook log is empty.[/yellow] No statistics to display.")
        raise SystemExit(_EXIT_SUCCESS)

    # Filter by session if requested
    if session_id and "session_id" in df.columns:
        df = df.filter(
            pl.col("session_id").cast(pl.Utf8).str.contains(session_id, literal=True)
        )
        if df.height == 0:
            console.print(
                f"[yellow]No entries found for session:[/yellow] {session_id}"
            )
            raise SystemExit(_EXIT_SUCCESS)

    stats = _compute_skill_stats(df)

    if format == OutputFormat.JSON:
        print(_format_skill_stats_json(stats))
    else:
        _render_skill_stats_rich(stats, console)

    raise SystemExit(_EXIT_SUCCESS)
