"""Built-in state updates for Claude Code hooks.

This module provides functions that update built-in session state
for each hook event type. All state keys use the 'oaps.' prefix.
"""

from typing import TYPE_CHECKING

from oaps.enums import HookEventType

# Runtime imports needed for type annotations (no `from __future__ import annotations`)
from ._inputs import (  # noqa: TC001
    HookInputT,
    NotificationInput,
    PermissionRequestInput,
    PostToolUseInput,
    PreCompactInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UserPromptSubmitInput,
)

if TYPE_CHECKING:
    from oaps.session import Session


def update_session_start(session: Session, hook_input: SessionStartInput) -> None:
    """Update state for session_start hook."""
    _ = session.set_timestamp("oaps.session.started_at")
    session.set("oaps.session.source", hook_input.source)


def update_session_end(session: Session, _hook_input: SessionEndInput) -> None:
    """Update state for session_end hook."""
    _ = session.set_timestamp("oaps.session.ended_at")


def update_user_prompt_submit(
    session: Session, _hook_input: UserPromptSubmitInput
) -> None:
    """Update state for user_prompt_submit hook."""
    _ = session.increment("oaps.prompts.count")
    _ = session.set_timestamp("oaps.prompts.last_at")
    _ = session.set_timestamp_if_absent("oaps.prompts.first_at")


def update_post_tool_use(session: Session, hook_input: PostToolUseInput) -> None:
    """Update state for post_tool_use hook."""
    tool_name = hook_input.tool_name
    _ = session.increment("oaps.tools.total_count")
    session.set("oaps.tools.last_tool", tool_name)
    _ = session.set_timestamp("oaps.tools.last_at")
    _ = session.increment(f"oaps.tools.{tool_name}.count")
    _ = session.set_timestamp(f"oaps.tools.{tool_name}.last_at")

    # Track subagent spawns
    if tool_name == "Task":
        _ = session.increment("oaps.subagents.spawn_count")


def update_permission_request(
    session: Session, hook_input: PermissionRequestInput
) -> None:
    """Update state for permission_request hook."""
    _ = session.increment("oaps.permissions.request_count")
    session.set("oaps.permissions.last_tool", hook_input.tool_name)


def update_notification(session: Session, hook_input: NotificationInput) -> None:
    """Update state for notification hook."""
    notification_type = hook_input.notification_type
    _ = session.increment("oaps.notifications.count")
    _ = session.increment(f"oaps.notifications.{notification_type}.count")


def update_stop(session: Session, _hook_input: StopInput) -> None:
    """Update state for stop hook."""
    _ = session.increment("oaps.session.stop_count")


def update_subagent_stop(session: Session, _hook_input: SubagentStopInput) -> None:
    """Update state for subagent_stop hook."""
    _ = session.increment("oaps.subagents.stop_count")


def update_pre_compact(session: Session, _hook_input: PreCompactInput) -> None:
    """Update state for pre_compact hook."""
    _ = session.increment("oaps.session.compaction_count")


# Dispatcher mapping hook event types to their state update functions.
# Each function takes (Session, specific_hook_input).
_STATE_UPDATERS: dict[HookEventType, object] = {
    HookEventType.SESSION_START: update_session_start,
    HookEventType.SESSION_END: update_session_end,
    HookEventType.USER_PROMPT_SUBMIT: update_user_prompt_submit,
    HookEventType.POST_TOOL_USE: update_post_tool_use,
    HookEventType.PERMISSION_REQUEST: update_permission_request,
    HookEventType.NOTIFICATION: update_notification,
    HookEventType.STOP: update_stop,
    HookEventType.SUBAGENT_STOP: update_subagent_stop,
    HookEventType.PRE_COMPACTION: update_pre_compact,
}


def update_hook_state(
    session: Session, event: HookEventType, hook_input: HookInputT
) -> None:
    """Dispatch to the appropriate state update function for the given event.

    Args:
        session: The session to update state in.
        event: The hook event type that triggered this update.
        hook_input: The validated input data for this hook.
    """
    updater = _STATE_UPDATERS.get(event)
    if updater is not None and callable(updater):
        _ = updater(session, hook_input)
