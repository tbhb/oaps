# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportUnknownVariableType=false
# ruff: noqa: A002, PLR0912, PLR0915, PLR2004, PLW2901
"""Candidates subcommand for hooks - identify patterns for potential hook rules."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import polars as pl
from cyclopts import Parameter
from rich.console import Console
from rich.table import Table

from oaps.cli._commands._context import OutputFormat
from oaps.cli._shared import get_time_range, parse_log_to_dataframe
from oaps.utils import get_oaps_hooks_log_file

from ._app import app
from ._exit_codes import EXIT_LOAD_ERROR, EXIT_SUCCESS

# Pattern extraction constants
_DEFAULT_MIN_COUNT = 5
_OAPS_CHAIN_MIN_COUNT = 2
_MAX_COMMAND_WORDS = 4


@dataclass(frozen=True, slots=True)
class HookCandidate:
    """A potential hook rule derived from usage patterns.

    Attributes:
        tool_name: The tool name (e.g., "Bash", "Read").
        pattern: Identifying pattern (command, path pattern).
        count: Number of occurrences.
        description: Human-readable description.
        category: One of "repeated_bash", "oaps_chain", "tool_pattern".
        example: Representative example, if available.
    """

    tool_name: str
    pattern: str
    count: int
    description: str
    category: str
    example: str | None


@dataclass(frozen=True, slots=True)
class CandidateAnalysis:
    """Complete analysis results.

    Attributes:
        total_events_analyzed: Total number of events analyzed.
        time_range_start: Earliest timestamp in analyzed data.
        time_range_end: Latest timestamp in analyzed data.
        candidates: List of identified hook candidates.
    """

    total_events_analyzed: int
    time_range_start: str | None
    time_range_end: str | None
    candidates: list[HookCandidate]


def _parse_time_filter(since: str | None) -> datetime | None:
    """Parse a time filter string into a datetime.

    Supports:
    - Relative formats: "1d" (1 day), "2h" (2 hours), "30m" (30 minutes)
    - Absolute formats: ISO 8601 dates like "2024-12-01" or "2024-12-01T10:30:00"

    Args:
        since: Time filter string, or None.

    Returns:
        datetime in UTC, or None if since is None.

    Raises:
        ValueError: If the format is invalid.
    """
    if since is None:
        return None

    # Try relative format first: e.g., "1d", "2h", "30m"
    relative_match = re.match(r"^(\d+)([dhm])$", since)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2)
        now = datetime.now(UTC)
        if unit == "d":
            return now - timedelta(days=amount)
        if unit == "h":
            return now - timedelta(hours=amount)
        if unit == "m":
            return now - timedelta(minutes=amount)

    # Try absolute ISO 8601 format
    try:
        parsed = datetime.fromisoformat(since)
    except ValueError:
        msg = (
            f"Invalid time format: {since!r}. "
            "Use relative (1d, 2h, 30m) or absolute (2024-12-01) format."
        )
        raise ValueError(msg) from None
    else:
        # Add UTC timezone if not specified
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed


def _extract_pre_tool_use_events(df: pl.DataFrame) -> pl.DataFrame:
    """Filter to hook_input events with PreToolUse.

    Args:
        df: DataFrame with parsed log entries.

    Returns:
        DataFrame filtered to PreToolUse hook_input events with extracted fields.
    """
    if "input" not in df.columns or "event" not in df.columns:
        return pl.DataFrame()

    # Filter to hook_input events
    hook_input_df = df.filter(
        (pl.col("event") == "hook_input") & pl.col("input").is_not_null()
    )
    if hook_input_df.height == 0:
        return pl.DataFrame()

    try:
        # Extract hook_event_name and tool_name from the input struct
        hook_input_df = hook_input_df.with_columns(
            [
                pl.col("input")
                .struct.field("hook_event_name")
                .alias("hook_event_name"),
                pl.col("input").struct.field("tool_name").alias("tool_name"),
                pl.col("input").struct.field("tool_input").alias("tool_input"),
            ]
        )
    except pl.exceptions.StructFieldNotFoundError:
        return pl.DataFrame()

    # Filter to PreToolUse events
    return hook_input_df.filter(pl.col("hook_event_name") == "PreToolUse")


def _normalize_bash_command(command: str) -> str:
    """Normalize a bash command by extracting key identifying words.

    Extracts first 3-4 significant words, skipping environment variable
    assignments and replacing absolute paths with relative ones.

    Args:
        command: The bash command string.

    Returns:
        Normalized command pattern.
    """
    # Skip leading env var assignments (FOO=bar ...)
    words = command.split()
    significant_words: list[str] = []

    for word in words:
        # Skip env var assignments
        if "=" in word and not word.startswith("-"):
            # Check if it's VAR=value pattern at start
            eq_idx = word.index("=")
            if eq_idx > 0 and word[:eq_idx].replace("_", "").isalnum():
                continue

        # Replace absolute paths with placeholders
        if word.startswith(("/Users/", "/home/")):
            word = "./..."
        elif word.startswith("/"):
            # Other absolute paths - keep the last component
            parts = word.split("/")
            if len(parts) > 2:
                word = f".../{parts[-1]}"

        significant_words.append(word)

        if len(significant_words) >= _MAX_COMMAND_WORDS:
            break

    return " ".join(significant_words)


def _extract_bash_patterns(df: pl.DataFrame, min_count: int) -> list[HookCandidate]:
    """Find repeated Bash commands.

    Args:
        df: DataFrame with PreToolUse events (already filtered).
        min_count: Minimum occurrence count to include.

    Returns:
        List of HookCandidate objects for repeated bash patterns.
    """
    if df.height == 0 or "tool_name" not in df.columns:
        return []

    # Filter to Bash tool events
    bash_df = df.filter(pl.col("tool_name") == "Bash")
    if bash_df.height == 0:
        return []

    # Extract command from tool_input struct
    try:
        bash_df = bash_df.with_columns(
            pl.col("tool_input").struct.field("command").alias("command")
        )
    except pl.exceptions.StructFieldNotFoundError:
        return []

    bash_df = bash_df.filter(pl.col("command").is_not_null())
    if bash_df.height == 0:
        return []

    # Normalize commands and group
    commands_with_normalized: list[tuple[str, str]] = []
    for row in bash_df.select("command").to_dicts():
        cmd = str(row["command"])
        normalized = _normalize_bash_command(cmd)
        if normalized:
            commands_with_normalized.append((normalized, cmd))

    if not commands_with_normalized:
        return []

    # Build a DataFrame for grouping
    cmd_df = pl.DataFrame(
        {
            "normalized": [c[0] for c in commands_with_normalized],
            "original": [c[1] for c in commands_with_normalized],
        }
    )

    # Group by normalized pattern
    grouped = (
        cmd_df.group_by("normalized")
        .agg(
            [
                pl.len().alias("count"),
                pl.col("original").first().alias("example"),
            ]
        )
        .filter(pl.col("count") >= min_count)
        .sort("count", descending=True)
    )

    candidates: list[HookCandidate] = []
    for row in grouped.to_dicts():
        pattern = str(row["normalized"])
        count = int(row["count"])
        example = str(row["example"]) if row["example"] else None

        # Generate description
        first_word = pattern.split()[0] if pattern else "command"
        description = f"Repeated '{first_word}' command pattern ({count}x)"

        candidates.append(
            HookCandidate(
                tool_name="Bash",
                pattern=pattern,
                count=count,
                description=description,
                category="repeated_bash",
                example=example,
            )
        )

    return candidates


def _extract_oaps_chains(df: pl.DataFrame, min_count: int) -> list[HookCandidate]:
    """Find Bash commands with 'oaps' and chaining operators.

    These are high-value candidates for automation hooks.

    Args:
        df: DataFrame with PreToolUse events (already filtered).
        min_count: Minimum occurrence count (uses lower threshold for chains).

    Returns:
        List of HookCandidate objects for oaps chain patterns.
    """
    _ = min_count  # Use lower threshold for chains

    if df.height == 0 or "tool_name" not in df.columns:
        return []

    # Filter to Bash tool events
    bash_df = df.filter(pl.col("tool_name") == "Bash")
    if bash_df.height == 0:
        return []

    # Extract command from tool_input struct
    try:
        bash_df = bash_df.with_columns(
            pl.col("tool_input").struct.field("command").alias("command")
        )
    except pl.exceptions.StructFieldNotFoundError:
        return []

    bash_df = bash_df.filter(pl.col("command").is_not_null())
    if bash_df.height == 0:
        return []

    # Filter to commands containing "oaps" and a chaining operator
    chain_operators = ["&&", "|", ";"]
    oaps_chains: list[str] = []

    for row in bash_df.select("command").to_dicts():
        cmd = str(row["command"])
        if "oaps" in cmd.lower():
            for op in chain_operators:
                if op in cmd:
                    oaps_chains.append(cmd)
                    break

    if not oaps_chains:
        return []

    # Normalize and group
    normalized_chains: list[tuple[str, str]] = []
    for cmd in oaps_chains:
        normalized = _normalize_bash_command(cmd)
        normalized_chains.append((normalized, cmd))

    chain_df = pl.DataFrame(
        {
            "normalized": [c[0] for c in normalized_chains],
            "original": [c[1] for c in normalized_chains],
        }
    )

    grouped = (
        chain_df.group_by("normalized")
        .agg(
            [
                pl.len().alias("count"),
                pl.col("original").first().alias("example"),
            ]
        )
        .filter(pl.col("count") >= _OAPS_CHAIN_MIN_COUNT)
        .sort("count", descending=True)
    )

    candidates: list[HookCandidate] = []
    for row in grouped.to_dicts():
        pattern = str(row["normalized"])
        count = int(row["count"])
        example = str(row["example"]) if row["example"] else None

        description = f"OAPS command chain pattern ({count}x) - automation candidate"

        candidates.append(
            HookCandidate(
                tool_name="Bash",
                pattern=pattern,
                count=count,
                description=description,
                category="oaps_chain",
                example=example,
            )
        )

    return candidates


def _extract_tool_patterns(df: pl.DataFrame, min_count: int) -> list[HookCandidate]:
    """Find generic tool+parameter patterns.

    Looks for patterns in Read file paths and other tools.

    Args:
        df: DataFrame with PreToolUse events (already filtered).
        min_count: Minimum occurrence count to include.

    Returns:
        List of HookCandidate objects for tool patterns.
    """
    if df.height == 0 or "tool_name" not in df.columns:
        return []

    candidates: list[HookCandidate] = []

    # Analyze Read tool file path patterns
    read_df = df.filter(pl.col("tool_name") == "Read")
    if read_df.height > 0:
        try:
            read_df = read_df.with_columns(
                pl.col("tool_input").struct.field("file_path").alias("file_path")
            )
            read_df = read_df.filter(pl.col("file_path").is_not_null())

            if read_df.height > 0:
                # Extract directory patterns from file paths
                path_patterns: list[tuple[str, str]] = []
                for row in read_df.select("file_path").to_dicts():
                    path = str(row["file_path"])
                    # Extract directory pattern (parent directories)
                    parts = path.split("/")
                    if len(parts) >= 2:
                        # Get parent directory or a recognizable pattern
                        if ".oaps" in path:
                            pattern = ".oaps/..."
                        elif "tests/" in path:
                            pattern = "tests/..."
                        elif "src/" in path:
                            pattern = "src/..."
                        elif len(parts) > 3:
                            pattern = f".../{parts[-2]}/"
                        else:
                            pattern = "/".join(parts[:-1]) + "/"
                        path_patterns.append((pattern, path))

                if path_patterns:
                    pattern_df = pl.DataFrame(
                        {
                            "pattern": [p[0] for p in path_patterns],
                            "original": [p[1] for p in path_patterns],
                        }
                    )

                    grouped = (
                        pattern_df.group_by("pattern")
                        .agg(
                            [
                                pl.len().alias("count"),
                                pl.col("original").first().alias("example"),
                            ]
                        )
                        .filter(pl.col("count") >= min_count)
                        .sort("count", descending=True)
                        .head(5)
                    )

                    for row in grouped.to_dicts():
                        pattern = str(row["pattern"])
                        count = int(row["count"])
                        example = str(row["example"]) if row["example"] else None

                        description = f"Frequent Read access to '{pattern}' ({count}x)"

                        candidates.append(
                            HookCandidate(
                                tool_name="Read",
                                pattern=pattern,
                                count=count,
                                description=description,
                                category="tool_pattern",
                                example=example,
                            )
                        )
        except pl.exceptions.StructFieldNotFoundError:
            pass

    # Analyze Write tool patterns
    write_df = df.filter(pl.col("tool_name") == "Write")
    if write_df.height > 0:
        try:
            write_df = write_df.with_columns(
                pl.col("tool_input").struct.field("file_path").alias("file_path")
            )
            write_df = write_df.filter(pl.col("file_path").is_not_null())

            if write_df.height > 0:
                path_patterns = []
                for row in write_df.select("file_path").to_dicts():
                    path = str(row["file_path"])
                    # Extract extension pattern
                    if "." in path:
                        ext = path.rsplit(".", 1)[-1]
                        pattern = f"*.{ext}"
                        path_patterns.append((pattern, path))

                if path_patterns:
                    pattern_df = pl.DataFrame(
                        {
                            "pattern": [p[0] for p in path_patterns],
                            "original": [p[1] for p in path_patterns],
                        }
                    )

                    grouped = (
                        pattern_df.group_by("pattern")
                        .agg(
                            [
                                pl.len().alias("count"),
                                pl.col("original").first().alias("example"),
                            ]
                        )
                        .filter(pl.col("count") >= min_count)
                        .sort("count", descending=True)
                        .head(5)
                    )

                    for row in grouped.to_dicts():
                        pattern = str(row["pattern"])
                        count = int(row["count"])
                        example = str(row["example"]) if row["example"] else None

                        description = f"Frequent Write to '{pattern}' files ({count}x)"

                        candidates.append(
                            HookCandidate(
                                tool_name="Write",
                                pattern=pattern,
                                count=count,
                                description=description,
                                category="tool_pattern",
                                example=example,
                            )
                        )
        except pl.exceptions.StructFieldNotFoundError:
            pass

    return candidates


def _compute_candidates(df: pl.DataFrame, min_count: int = 5) -> CandidateAnalysis:
    """Compute hook candidates from the log DataFrame.

    Args:
        df: DataFrame with parsed log entries.
        min_count: Minimum count threshold for patterns.

    Returns:
        CandidateAnalysis with all identified candidates.
    """
    total_events = df.height
    time_range_start, time_range_end = get_time_range(df)

    # Extract PreToolUse events
    pre_tool_df = _extract_pre_tool_use_events(df)

    candidates: list[HookCandidate] = []

    # Extract patterns from different categories
    candidates.extend(_extract_bash_patterns(pre_tool_df, min_count))
    candidates.extend(_extract_oaps_chains(pre_tool_df, min_count))
    candidates.extend(_extract_tool_patterns(pre_tool_df, min_count))

    # Sort by count descending
    candidates.sort(key=lambda c: c.count, reverse=True)

    return CandidateAnalysis(
        total_events_analyzed=total_events,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        candidates=candidates,
    )


def _render_rich_output(analysis: CandidateAnalysis, console: Console) -> None:
    """Render candidates using Rich for terminal output.

    Args:
        analysis: CandidateAnalysis results.
        console: Rich console for output.
    """
    console.print()
    count = len(analysis.candidates)
    events = analysis.total_events_analyzed
    console.print(
        f"[bold blue]Hook Candidates[/bold blue] ({count} found from {events:,} events)"
    )

    if analysis.time_range_start and analysis.time_range_end:
        start = analysis.time_range_start
        end = analysis.time_range_end
        console.print(f"[dim]Time range: {start} → {end}[/dim]")
    console.print()

    if not analysis.candidates:
        no_candidates_msg = (
            "[yellow]No hook candidates found.[/yellow] "
            "Try lowering --min-count or expanding --since."
        )
        console.print(no_candidates_msg)
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Category", style="cyan", width=14)
    table.add_column("Tool", width=8)
    table.add_column("Pattern", width=35)
    table.add_column("Count", justify="right", width=6)
    table.add_column("Example", width=40, overflow="ellipsis")

    category_styles = {
        "repeated_bash": "yellow",
        "oaps_chain": "green",
        "tool_pattern": "blue",
    }

    for candidate in analysis.candidates:
        style = category_styles.get(candidate.category, "")
        category_display = candidate.category.replace("_", " ").title()

        example_display = candidate.example or ""
        if len(example_display) > 40:
            example_display = example_display[:37] + "..."

        table.add_row(
            f"[{style}]{category_display}[/{style}]" if style else category_display,
            candidate.tool_name,
            candidate.pattern,
            str(candidate.count),
            example_display,
        )

    console.print(table)
    console.print()


def _format_markdown_output(analysis: CandidateAnalysis) -> str:
    """Format candidates as detailed Markdown.

    Args:
        analysis: CandidateAnalysis results.

    Returns:
        Markdown formatted string.
    """
    from pytablewriter import MarkdownTableWriter

    lines: list[str] = []

    lines.append("# Hook Candidates Analysis")
    lines.append("")
    lines.append(f"**Events analyzed:** {analysis.total_events_analyzed:,}")
    if analysis.time_range_start and analysis.time_range_end:
        lines.append(
            f"**Time range:** {analysis.time_range_start} to {analysis.time_range_end}"
        )
    lines.append(f"**Candidates found:** {len(analysis.candidates)}")
    lines.append("")

    if not analysis.candidates:
        lines.append("*No hook candidates found.*")
        return "\n".join(lines)

    # Group by category
    by_category: dict[str, list[HookCandidate]] = {}
    for candidate in analysis.candidates:
        if candidate.category not in by_category:
            by_category[candidate.category] = []
        by_category[candidate.category].append(candidate)

    category_titles = {
        "oaps_chain": "OAPS Command Chains (High-Value Automation Candidates)",
        "repeated_bash": "Repeated Bash Commands",
        "tool_pattern": "Tool Usage Patterns",
    }

    for category in ["oaps_chain", "repeated_bash", "tool_pattern"]:
        if category not in by_category:
            continue

        candidates = by_category[category]
        title = category_titles.get(category, category.replace("_", " ").title())

        lines.append(f"## {title}")
        lines.append("")

        writer = MarkdownTableWriter(
            headers=["Tool", "Pattern", "Count", "Description"],
            value_matrix=[
                [c.tool_name, c.pattern, c.count, c.description] for c in candidates
            ],
        )
        lines.append(writer.dumps())
        lines.append("")

        # Add examples section
        lines.append("### Examples")
        lines.append("")
        for c in candidates[:3]:  # Show first 3 examples
            if c.example:
                lines.append(f"- **{c.pattern}**")
                lines.append("  ```")
                lines.append(f"  {c.example}")
                lines.append("  ```")
        lines.append("")

    return "\n".join(lines)


def _format_json_output(analysis: CandidateAnalysis) -> str:
    """Format candidates as JSON.

    Args:
        analysis: CandidateAnalysis results.

    Returns:
        JSON string output.
    """
    import orjson

    data = {
        "total_events_analyzed": analysis.total_events_analyzed,
        "time_range": {
            "start": analysis.time_range_start,
            "end": analysis.time_range_end,
        },
        "candidates": [
            {
                "tool_name": c.tool_name,
                "pattern": c.pattern,
                "count": c.count,
                "description": c.description,
                "category": c.category,
                "example": c.example,
            }
            for c in analysis.candidates
        ],
    }

    return orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8")


@app.command(name="candidates")
def _candidates(
    *,
    since: Annotated[
        str,
        Parameter(
            name=["--since", "-s"],
            help="Analyze events since this time (e.g., 7d, 24h, 30m, or 2024-12-01)",
        ),
    ] = "7d",
    min_count: Annotated[
        int,
        Parameter(
            name=["--min-count", "-n"],
            help="Minimum occurrence count to include as candidate",
        ),
    ] = _DEFAULT_MIN_COUNT,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, plain/markdown, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Identify potential hook rules from usage patterns.

    Analyzes the hook log to find repeated patterns that could benefit
    from hook automation. Categories include:

    - Repeated Bash: Commands run frequently (potential for automation)
    - OAPS Chains: oaps commands with && or | (workflow candidates)
    - Tool Patterns: Frequent file access patterns

    Examples:
        oaps hooks candidates                     # Last 7 days, min 5 occurrences
        oaps hooks candidates -n 3                # Lower threshold
        oaps hooks candidates --since 24h         # Last 24 hours
        oaps hooks candidates -f plain            # Markdown for review/documentation
        oaps hooks candidates -f json             # For programmatic use

    Exit codes:
        0: Analysis completed successfully
        1: Failed to load or parse log file
    """
    console = Console()
    log_path = get_oaps_hooks_log_file()

    if not log_path.exists():
        if format == OutputFormat.JSON:
            print(
                _format_json_output(
                    CandidateAnalysis(
                        total_events_analyzed=0,
                        time_range_start=None,
                        time_range_end=None,
                        candidates=[],
                    )
                )
            )
        else:
            console.print(f"[yellow]Hook log file not found:[/yellow] {log_path}")
            console.print("No hook executions have been recorded yet.")
        raise SystemExit(EXIT_SUCCESS)

    try:
        df = parse_log_to_dataframe(str(log_path))
    except pl.exceptions.ComputeError as e:
        console.print(f"[red]Error parsing hook log:[/red] {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    if df.height == 0:
        if format == OutputFormat.JSON:
            print(
                _format_json_output(
                    CandidateAnalysis(
                        total_events_analyzed=0,
                        time_range_start=None,
                        time_range_end=None,
                        candidates=[],
                    )
                )
            )
        else:
            console.print("[yellow]Hook log is empty.[/yellow] No patterns to analyze.")
        raise SystemExit(EXIT_SUCCESS)

    # Parse time filter and apply
    since_dt: datetime | None = None
    try:
        since_dt = _parse_time_filter(since)
    except ValueError as e:
        console.print(f"[red]Invalid --since value:[/red] {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    # Filter by time if specified
    if since_dt is not None and "timestamp" in df.columns:
        since_str = since_dt.isoformat()
        df = df.filter(pl.col("timestamp") >= since_str)

        if df.height == 0:
            if format == OutputFormat.JSON:
                print(
                    _format_json_output(
                        CandidateAnalysis(
                            total_events_analyzed=0,
                            time_range_start=None,
                            time_range_end=None,
                            candidates=[],
                        )
                    )
                )
            else:
                no_events_msg = (
                    f"[yellow]No events found since {since}.[/yellow] "
                    "Try expanding the time range."
                )
                console.print(no_events_msg)
            raise SystemExit(EXIT_SUCCESS)

    # Compute candidates
    analysis = _compute_candidates(df, min_count)

    # Output based on format
    if format == OutputFormat.JSON:
        print(_format_json_output(analysis))
    elif format == OutputFormat.PLAIN:
        print(_format_markdown_output(analysis))
    else:
        _render_rich_output(analysis, console)

    raise SystemExit(EXIT_SUCCESS)
