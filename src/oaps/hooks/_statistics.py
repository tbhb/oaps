"""Session statistics gathering and formatting for hooks.

This module provides functions to gather session statistics from the session
store and format them for context injection during pre-compaction.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.session import Session


@dataclass(frozen=True, slots=True)
class SessionStatistics:
    """Aggregated statistics from a session store.

    Attributes:
        started_at: When the session started (ISO 8601 timestamp).
        ended_at: When the session ended (ISO 8601 timestamp).
        source: How the session was started (e.g., "startup", "resume").
        prompt_count: Total number of user prompts submitted.
        first_prompt_at: When the first prompt was submitted.
        last_prompt_at: When the most recent prompt was submitted.
        total_tool_count: Total number of tool invocations.
        last_tool: Name of the most recently used tool.
        last_tool_at: When the last tool was used.
        tool_counts: Mapping of tool name to invocation count.
        permission_request_count: Total permission requests.
        last_permission_tool: Tool that triggered the last permission request.
        notification_count: Total notifications received.
        notification_counts: Mapping of notification type to count.
        stop_count: Number of times the session was stopped.
        compaction_count: Number of context compactions performed.
        subagent_spawn_count: Number of subagents spawned.
        subagent_stop_count: Number of subagents that stopped.
    """

    # Timestamps
    started_at: str | None
    ended_at: str | None
    source: str | None

    # Prompt statistics
    prompt_count: int
    first_prompt_at: str | None
    last_prompt_at: str | None

    # Tool statistics
    total_tool_count: int
    last_tool: str | None
    last_tool_at: str | None
    tool_counts: dict[str, int]

    # Permission statistics
    permission_request_count: int
    last_permission_tool: str | None

    # Notification statistics
    notification_count: int
    notification_counts: dict[str, int]

    # Session control
    stop_count: int
    compaction_count: int

    # Subagent statistics
    subagent_spawn_count: int
    subagent_stop_count: int


def _get_int(session: Session, key: str) -> int:
    """Get an integer value from session, defaulting to 0."""
    value = session.get(key)
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _get_str(session: Session, key: str) -> str | None:
    """Get a string value from session, returning None if not found."""
    value = session.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def gather_session_statistics(session: Session) -> SessionStatistics:
    """Gather all tracked statistics from session state.

    Iterates through session store keys to discover tool and notification
    counts dynamically.

    Args:
        session: The session to gather statistics from.

    Returns:
        A SessionStatistics dataclass with all gathered statistics.
    """
    # Key structure constants for parsing oaps.X.Y.Z patterns
    expected_parts_count = 4  # e.g., oaps.tools.Read.count has 4 parts
    name_part_index = 2  # The name is always at index 2

    # Gather tool counts by scanning keys
    tool_counts: dict[str, int] = {}
    notification_counts: dict[str, int] = {}

    for key in session.store:
        # Match pattern: oaps.tools.<tool_name>.count
        if key.startswith("oaps.tools.") and key.endswith(".count"):
            # Extract tool name from oaps.tools.<name>.count
            parts = key.split(".")
            if len(parts) == expected_parts_count:
                tool_name = parts[name_part_index]
                if tool_name != "total":  # Skip total_count
                    tool_counts[tool_name] = _get_int(session, key)

        # Match pattern: oaps.notifications.<type>.count
        if key.startswith("oaps.notifications.") and key.endswith(".count"):
            parts = key.split(".")
            if len(parts) == expected_parts_count:
                notification_type = parts[name_part_index]
                notification_counts[notification_type] = _get_int(session, key)

    return SessionStatistics(
        # Session timestamps
        started_at=_get_str(session, "oaps.session.started_at"),
        ended_at=_get_str(session, "oaps.session.ended_at"),
        source=_get_str(session, "oaps.session.source"),
        # Prompt statistics
        prompt_count=_get_int(session, "oaps.prompts.count"),
        first_prompt_at=_get_str(session, "oaps.prompts.first_at"),
        last_prompt_at=_get_str(session, "oaps.prompts.last_at"),
        # Tool statistics
        total_tool_count=_get_int(session, "oaps.tools.total_count"),
        last_tool=_get_str(session, "oaps.tools.last_tool"),
        last_tool_at=_get_str(session, "oaps.tools.last_at"),
        tool_counts=tool_counts,
        # Permission statistics
        permission_request_count=_get_int(session, "oaps.permissions.request_count"),
        last_permission_tool=_get_str(session, "oaps.permissions.last_tool"),
        # Notification statistics
        notification_count=_get_int(session, "oaps.notifications.count"),
        notification_counts=notification_counts,
        # Session control
        stop_count=_get_int(session, "oaps.session.stop_count"),
        compaction_count=_get_int(session, "oaps.session.compaction_count"),
        # Subagent statistics
        subagent_spawn_count=_get_int(session, "oaps.subagents.spawn_count"),
        subagent_stop_count=_get_int(session, "oaps.subagents.stop_count"),
    )


def format_statistics_context(stats: SessionStatistics) -> str:
    """Format session statistics as context for Claude.

    Produces a human-readable summary suitable for injection into the
    conversation context during pre-compaction.

    Args:
        stats: The session statistics to format.

    Returns:
        A formatted string containing the session statistics.
    """
    lines: list[str] = []

    lines.append("=== OAPS Session Statistics ===")
    lines.append("")

    # Session section
    lines.append("Session:")
    if stats.started_at:
        lines.append(f"  Started: {stats.started_at}")
    if stats.ended_at:
        lines.append(f"  Ended: {stats.ended_at}")
    if stats.source:
        lines.append(f"  Source: {stats.source}")
    lines.append(f"  Compactions: {stats.compaction_count}")
    lines.append(f"  Stops: {stats.stop_count}")
    lines.append("")

    # Prompts section
    lines.append("Prompts:")
    lines.append(f"  Total: {stats.prompt_count}")
    if stats.first_prompt_at:
        lines.append(f"  First: {stats.first_prompt_at}")
    if stats.last_prompt_at:
        lines.append(f"  Last: {stats.last_prompt_at}")
    lines.append("")

    # Tools section
    lines.append("Tools:")
    lines.append(f"  Total invocations: {stats.total_tool_count}")
    if stats.last_tool:
        last_tool_info = stats.last_tool
        if stats.last_tool_at:
            last_tool_info = f"{stats.last_tool} ({stats.last_tool_at})"
        lines.append(f"  Last tool: {last_tool_info}")
    if stats.tool_counts:
        lines.append("  By tool:")
        # Sort by count descending for readability
        sorted_tools = sorted(
            stats.tool_counts.items(), key=lambda x: x[1], reverse=True
        )
        for tool_name, count in sorted_tools:
            lines.append(f"    {tool_name}: {count}")
    lines.append("")

    # Permissions section
    lines.append("Permissions:")
    lines.append(f"  Total requests: {stats.permission_request_count}")
    if stats.last_permission_tool:
        lines.append(f"  Last tool: {stats.last_permission_tool}")
    lines.append("")

    # Notifications section
    lines.append("Notifications:")
    lines.append(f"  Total: {stats.notification_count}")
    if stats.notification_counts:
        lines.append("  By type:")
        sorted_notifications = sorted(
            stats.notification_counts.items(), key=lambda x: x[1], reverse=True
        )
        for notification_type, count in sorted_notifications:
            lines.append(f"    {notification_type}: {count}")
    lines.append("")

    # Subagents section
    lines.append("Subagents:")
    lines.append(f"  Spawned: {stats.subagent_spawn_count}")
    lines.append(f"  Stopped: {stats.subagent_stop_count}")

    return "\n".join(lines)
