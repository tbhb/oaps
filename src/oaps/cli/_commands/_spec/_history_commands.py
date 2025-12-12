# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportAny=false
# ruff: noqa: D415, PLR0913
"""History plumbing commands.

This module provides commands for querying specification history.
Commands: show.
"""

from typing import Annotated

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.cli._commands._shared import exit_with_error, exit_with_success
from oaps.exceptions import SpecNotFoundError

from ._errors import exit_code_for_exception
from ._helpers import (
    get_history_manager,
    history_entry_to_dict,
    parse_time_filter,
)
from ._history_app import history_app
from ._output import format_history_info, format_history_table, format_json

__all__ = ["show"]


@history_app.command(name="show")
def show(
    spec_id: str,
    /,
    *,
    since: Annotated[
        str | None,
        Parameter(
            name=["--since"],
            help="Show entries from this time (e.g., 1d, 2h, 30m, or ISO 8601)",
        ),
    ] = None,
    until: Annotated[
        str | None,
        Parameter(
            name=["--until"],
            help="Show entries until this time (e.g., 1d, 2h, 30m, or ISO 8601)",
        ),
    ] = None,
    event: Annotated[
        str | None,
        Parameter(
            name=["--event", "-e"], help="Filter by event type (substring match)"
        ),
    ] = None,
    actor: Annotated[
        str | None,
        Parameter(name=["--actor", "-a"], help="Filter by actor (exact match)"),
    ] = None,
    limit: Annotated[
        int,
        Parameter(name=["--limit", "-n"], help="Maximum number of entries to show"),
    ] = 50,
    format_: Annotated[
        OutputFormat,
        Parameter(name=["--format", "-f"], help="Output format"),
    ] = OutputFormat.TABLE,
) -> None:
    """Show specification history entries

    Args:
        spec_id: The specification ID.
        since: Show entries from this time (relative or ISO 8601).
        until: Show entries until this time (relative or ISO 8601).
        event: Filter by event type (substring match).
        actor: Filter by actor (exact match).
        limit: Maximum number of entries to return.
        format_: Output format.
    """
    try:
        # Parse time filters
        since_dt = parse_time_filter(since)
        until_dt = parse_time_filter(until)

        manager = get_history_manager()
        entries = manager.get(
            spec_id,
            since=since_dt,
            until=until_dt,
            event_filter=event,
            actor_filter=actor,
            limit=limit,
        )

        entry_dicts = [history_entry_to_dict(e) for e in entries]
        _print_history_result(entry_dicts, format_)

    except (SpecNotFoundError, ValueError) as e:
        exit_with_error(str(e), exit_code_for_exception(e))


def _print_history_result(
    entries: list[dict[str, object]], format_: OutputFormat
) -> None:
    """Print history result and exit with success.

    Args:
        entries: List of history entry dictionaries.
        format_: The output format to use.

    Raises:
        SystemExit: Always exits with EXIT_SUCCESS (0).
    """
    from ._output import format_yaml

    output: str
    if format_ == OutputFormat.TABLE:
        output = format_history_table(entries)
    elif format_ == OutputFormat.JSON:
        output = format_json({"entries": entries})
    elif format_ == OutputFormat.YAML:
        output = format_yaml({"entries": entries})
    elif format_ in (OutputFormat.TEXT, OutputFormat.PLAIN):
        # Show detailed info for single entry, table for multiple
        if len(entries) == 1:
            output = format_history_info(entries[0])
        else:
            output = format_history_table(entries)
    else:
        # TOML format
        import tomli_w

        output = tomli_w.dumps({"entries": entries})

    print(output)
    exit_with_success()
