# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportExplicitAny=false, reportAny=false
# ruff: noqa: D415, A002, BLE001, PLR0912, PLR0915, PERF401
"""Status subcommand for hooks."""

from collections import Counter
from typing import Annotated, Any

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import ExitCode, exit_with_error, exit_with_success
from oaps.config import (
    HookRuleConfiguration,
    RulePriority,
    discover_drop_in_files,
    find_project_root,
    get_user_config_path,
    load_all_hook_rules,
)
from oaps.utils import create_hooks_logger, get_oaps_state_file

from ._app import app


def _count_by_priority(rules: list[HookRuleConfiguration]) -> dict[str, int]:
    """Count rules by priority level.

    Args:
        rules: List of rules to count.

    Returns:
        Dictionary mapping priority names to counts.
    """
    counter: Counter[str] = Counter()
    for rule in rules:
        counter[rule.priority.value] += 1

    # Return in priority order
    result: dict[str, int] = {}
    for prio in RulePriority:
        result[prio.value] = counter.get(prio.value, 0)
    return result


def _count_by_event(rules: list[HookRuleConfiguration]) -> dict[str, int]:
    """Count rules by event type.

    Args:
        rules: List of rules to count.

    Returns:
        Dictionary mapping event types to counts.
    """
    counter: Counter[str] = Counter()
    for rule in rules:
        for event in rule.events:
            counter[event] += 1
    return dict(sorted(counter.items()))


def _count_by_source(rules: list[HookRuleConfiguration]) -> dict[str, int]:
    """Count rules by source file.

    Args:
        rules: List of rules to count.

    Returns:
        Dictionary mapping source file names to counts.
    """
    counter: Counter[str] = Counter()
    for rule in rules:
        if rule.source_file:
            counter[rule.source_file.name] += 1
        else:
            counter["(unknown)"] += 1
    return dict(sorted(counter.items()))


def _get_config_locations() -> dict[str, str | None]:
    """Get locations of hook configuration files.

    Returns:
        Dictionary mapping source names to file paths.
    """
    project_root = find_project_root()
    user_config = get_user_config_path()

    locations: dict[str, str | None] = {
        "user_config": str(user_config) if user_config.exists() else None,
    }

    if project_root:
        oaps_dir = project_root / ".oaps"
        locations["project_hooks"] = (
            str(oaps_dir / "hooks.toml") if (oaps_dir / "hooks.toml").exists() else None
        )
        locations["project_config"] = (
            str(oaps_dir / "oaps.toml") if (oaps_dir / "oaps.toml").exists() else None
        )
        locations["local_config"] = (
            str(oaps_dir / "oaps.local.toml")
            if (oaps_dir / "oaps.local.toml").exists()
            else None
        )

        # Drop-in directory
        dropin_dir = oaps_dir / "hooks.d"
        if dropin_dir.exists():
            files = discover_drop_in_files(dropin_dir)
            locations["dropin_directory"] = str(dropin_dir)
            locations["dropin_files"] = str(len(files))
        else:
            locations["dropin_directory"] = None
            locations["dropin_files"] = "0"
    else:
        locations["project_root"] = None

    return locations


def _get_recent_sessions(limit: int = 5) -> list[dict[str, Any]]:
    """Get recent session information from the unified state database.

    Args:
        limit: Maximum number of sessions to return.

    Returns:
        List of session info dictionaries.
    """
    state_file = get_oaps_state_file()
    if not state_file.exists():
        return []

    # Query the unified database for distinct session IDs with recent activity
    import sqlite3

    sessions: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(state_file) as conn:
            cursor = conn.execute(
                """
                SELECT session_id,
                       MAX(updated_at) as last_activity,
                       COUNT(*) as entry_count
                FROM state_store
                WHERE session_id != ''
                GROUP BY session_id
                ORDER BY last_activity DESC
                LIMIT ?
                """,
                (limit,),
            )
            for row in cursor:
                sessions.append(
                    {
                        "session_id": row[0],
                        "last_activity": row[1],
                        "entry_count": row[2],
                    }
                )
    except sqlite3.Error:
        # Database might not exist or have expected schema
        return []

    return sessions


@app.command(name="status")
def _status(
    *,
    session_id: Annotated[
        str | None,
        Parameter(
            name=["--session", "-s"],
            help="Show details for specific session",
        ),
    ] = None,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (text, json)",
        ),
    ] = OutputFormat.TEXT,
) -> None:
    """Show hook system status and configuration summary

    Displays:
    - Configuration file locations
    - Number of rules by priority and event
    - Recent session information (if available)

    Use --session to filter to a specific session's hook executions.

    Exit codes:
        0: Status displayed successfully
        1: Failed to load configuration
    """
    logger = create_hooks_logger()

    # Resolve project root
    project_root = find_project_root()

    # Load all rules
    try:
        rules = load_all_hook_rules(project_root, logger)
    except Exception as e:
        exit_with_error(f"Loading hook rules: {e}", ExitCode.LOAD_ERROR)

    # Gather statistics
    enabled_count = sum(1 for r in rules if r.enabled)
    disabled_count = len(rules) - enabled_count
    by_priority = _count_by_priority(rules)
    by_event = _count_by_event(rules)
    by_source = _count_by_source(rules)
    locations = _get_config_locations()
    recent_sessions = _get_recent_sessions()

    # Filter sessions if requested
    if session_id:
        recent_sessions = [s for s in recent_sessions if session_id in s["session_id"]]

    # Format output
    if format == OutputFormat.JSON:
        import orjson

        data = {
            "project_root": str(project_root) if project_root else None,
            "config_locations": locations,
            "rules": {
                "total": len(rules),
                "enabled": enabled_count,
                "disabled": disabled_count,
                "by_priority": by_priority,
                "by_event": by_event,
                "by_source": by_source,
            },
            "sessions": recent_sessions,
        }
        print(orjson.dumps(data, option=orjson.OPT_INDENT_2).decode("utf-8"))
    else:
        print("=" * 60)
        print("HOOK SYSTEM STATUS")
        print("=" * 60)
        print()

        # Project info
        print("Project:")
        if project_root:
            print(f"  Root: {project_root}")
        else:
            print("  Root: Not in a project directory")
        print()

        # Configuration locations
        print("Configuration Files:")
        for name, path in locations.items():
            if name in ("dropin_files",):
                continue
            display_name = name.replace("_", " ").title()
            if path:
                print(f"  {display_name}: {path}")
            else:
                print(f"  {display_name}: (not found)")
        print()

        # Rule counts
        print("Rules:")
        print(f"  Total: {len(rules)}")
        print(f"  Enabled: {enabled_count}")
        print(f"  Disabled: {disabled_count}")
        print()

        print("  By Priority:")
        for prio, count in by_priority.items():
            if count > 0:
                print(f"    {prio}: {count}")
        print()

        print("  By Event:")
        for event, count in by_event.items():
            print(f"    {event}: {count}")
        print()

        print("  By Source:")
        for source, count in by_source.items():
            print(f"    {source}: {count}")
        print()

        # Recent sessions
        if recent_sessions:
            print("Recent Sessions:")
            for sess in recent_sessions:
                entry_count = sess["entry_count"]
                last_activity = sess.get("last_activity", "unknown")
                session_preview = sess["session_id"][:16]
                print(
                    f"  {session_preview}... "
                    f"({entry_count} entries, last: {last_activity})"
                )
        else:
            print("Recent Sessions: None found")
        print()

    exit_with_success()
