"""Enumeration types for OAPS."""

from enum import StrEnum


class HookEventType(StrEnum):
    """Claude Code hook event types."""

    PRE_TOOL_USE = "pre_tool_use"
    PERMISSION_REQUEST = "permission_request"
    POST_TOOL_USE = "post_tool_use"
    NOTIFICATION = "notification"
    USER_PROMPT_SUBMIT = "user_prompt_submit"
    STOP = "stop"
    SUBAGENT_STOP = "subagent_stop"
    PRE_COMPACTION = "pre_compact"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
