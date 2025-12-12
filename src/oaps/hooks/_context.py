from dataclasses import dataclass
from typing import TYPE_CHECKING

from oaps.hooks._inputs import (
    HookInputT,
    is_notification_hook,
    is_permission_request_hook,
    is_post_tool_use_hook,
    is_pre_compact_hook,
    is_pre_tool_use_hook,
    is_session_start_hook,
    is_stop_hook,
    is_subagent_stop_hook,
    is_user_prompt_submit_hook,
)

if TYPE_CHECKING:
    from pathlib import Path

    from structlog.typing import FilteringBoundLogger

    from oaps.enums import HookEventType
    from oaps.project import ProjectContext
    from oaps.utils import GitContext


@dataclass(slots=True, frozen=True)
class HookContext:
    """Context information for hooks."""

    hook_event_type: HookEventType
    hook_input: HookInputT

    claude_session_id: str

    oaps_dir: Path
    oaps_state_file: Path

    hook_logger: FilteringBoundLogger
    session_logger: FilteringBoundLogger

    git: GitContext | None = None
    project: ProjectContext | None = None


def is_pre_tool_use_context(context: HookContext) -> bool:
    return is_pre_tool_use_hook(context.hook_input)


def is_post_tool_use_context(context: HookContext) -> bool:
    return is_post_tool_use_hook(context.hook_input)


def is_user_prompt_submit_context(context: HookContext) -> bool:
    return is_user_prompt_submit_hook(context.hook_input)


def is_permission_request_context(context: HookContext) -> bool:
    return is_permission_request_hook(context.hook_input)


def is_notification_context(context: HookContext) -> bool:
    return is_notification_hook(context.hook_input)


def is_session_start_context(context: HookContext) -> bool:
    return is_session_start_hook(context.hook_input)


def is_stop_context(context: HookContext) -> bool:
    return is_stop_hook(context.hook_input)


def is_subagent_stop_context(context: HookContext) -> bool:
    return is_subagent_stop_hook(context.hook_input)


def is_pre_compact_context(context: HookContext) -> bool:
    return is_pre_compact_hook(context.hook_input)
