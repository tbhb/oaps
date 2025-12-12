"""Pydantic models for Claude Code hook inputs."""

from pathlib import Path  # noqa: TC003
from typing import ClassVar, Literal, TypeIs
from uuid import UUID  # noqa: TC003

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from oaps.enums import HookEventType


class ReadToolInput(BaseModel):
    """Input parameters for the Read tool."""

    file_path: str = Field(..., description="Absolute path to the file to read")
    offset: int | None = Field(
        None, description="Line number to start reading from (0-indexed)"
    )
    limit: int | None = Field(None, description="Maximum number of lines to read")


class WriteToolInput(BaseModel):
    """Input parameters for the Write tool."""

    file_path: str = Field(..., description="Absolute path to the file to write")
    content: str = Field(..., description="Content to write to the file")


class EditToolInput(BaseModel):
    """Input parameters for the Edit tool."""

    file_path: str = Field(..., description="Absolute path to the file to edit")
    old_string: str = Field(..., description="Text to find and replace")
    new_string: str = Field(..., description="Replacement text")
    replace_all: bool | None = Field(
        None, description="Replace all occurrences (default: false)"
    )


class MultiEditOperation(BaseModel):
    """A single edit operation within a MultiEdit."""

    old_string: str = Field(..., description="Text to find and replace")
    new_string: str = Field(..., description="Replacement text")


class MultiEditToolInput(BaseModel):
    """Input parameters for the MultiEdit tool."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    file_path: str = Field(..., description="Absolute path to the file to edit")
    edits: list[MultiEditOperation] = Field(..., description="Array of edit operations")


class GlobToolInput(BaseModel):
    """Input parameters for the Glob tool."""

    pattern: str = Field(..., description="Glob pattern to match files")
    path: str | None = Field(None, description="Directory to search in (default: cwd)")


class NotebookEditToolInput(BaseModel):
    """Input parameters for the NotebookEdit tool."""

    notebook_path: str = Field(..., description="Absolute path to the Jupyter notebook")
    new_source: str = Field(..., description="New source code for the cell")
    cell_id: str | None = Field(None, description="ID of the cell to edit")
    cell_type: Literal["code", "markdown"] | None = Field(None, description="Cell type")
    edit_mode: Literal["replace", "insert", "delete"] | None = Field(
        None, description="Edit mode"
    )


class GrepToolInput(BaseModel):
    """Input parameters for the Grep tool."""

    pattern: str = Field(..., description="Regular expression pattern to search for")
    path: str | None = Field(
        None, description="File or directory to search in (default: cwd)"
    )
    output_mode: Literal["content", "files_with_matches", "count"] | None = Field(
        None, description="Output format"
    )
    glob: str | None = Field(None, description="Glob pattern to filter files")
    type: str | None = Field(None, description="File type filter")
    after: int | None = Field(
        None, alias="-A", description="Lines to show after each match"
    )
    before: int | None = Field(
        None, alias="-B", description="Lines to show before each match"
    )
    context: int | None = Field(
        None, alias="-C", description="Lines to show before and after each match"
    )
    ignore_case: bool | None = Field(
        None, alias="-i", description="Case-insensitive search"
    )
    show_line_numbers: bool | None = Field(
        None, alias="-n", description="Show line numbers in output"
    )
    multiline: bool | None = Field(
        None, description="Enable multiline matching (default: false)"
    )
    head_limit: int | None = Field(
        None, description="Limit output to first N lines/entries"
    )
    offset: int | None = Field(
        None, description="Skip first N lines/entries before applying head_limit"
    )


class BashToolInput(BaseModel):
    """Input parameters for the Bash tool."""

    command: str = Field(..., description="Shell command to execute")
    description: str | None = Field(
        None, description="Human-readable description of the command"
    )
    timeout: int | None = Field(
        None, description="Timeout in milliseconds (max: 600000)"
    )
    run_in_background: bool | None = Field(
        None, description="Run command in background (default: false)"
    )
    dangerously_disable_sandbox: bool | None = Field(
        None, description="Disable sandbox mode (default: false)"
    )


class BashOutputToolInput(BaseModel):
    """Input parameters for the BashOutput tool."""

    bash_id: str = Field(
        ..., description="ID of the background shell to retrieve output from"
    )
    filter: str | None = Field(None, description="Regex pattern to filter output lines")


class KillShellToolInput(BaseModel):
    """Input parameters for the KillShell tool."""

    shell_id: str = Field(..., description="ID of the background shell to terminate")


class WebFetchToolInput(BaseModel):
    """Input parameters for the WebFetch tool."""

    url: str = Field(..., description="URL to fetch content from")
    prompt: str = Field(
        ..., description="Prompt describing what to extract from the content"
    )


class WebSearchToolInput(BaseModel):
    """Input parameters for the WebSearch tool."""

    query: str = Field(..., description="Search query string")
    allowed_domains: list[str] | None = Field(
        None, description="Only include results from these domains"
    )
    blocked_domains: list[str] | None = Field(
        None, description="Exclude results from these domains"
    )


class TaskToolInput(BaseModel):
    """Input parameters for the Task tool."""

    prompt: str = Field(..., description="Instructions for the subagent")
    description: str | None = Field(
        None, description="Human-readable description of the task"
    )
    subagent_type: str | None = Field(None, description="Type of subagent to spawn")


class TodoItem(BaseModel):
    """A single todo item."""

    content: str = Field(..., description="Todo item description")
    status: Literal["pending", "in_progress", "completed"] = Field(
        ..., description="Status of the todo item"
    )
    active_form: str = Field(..., description="Present-tense description of the task")


class TodoWriteToolInput(BaseModel):
    """Input parameters for the TodoWrite tool."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    todos: list[TodoItem] = Field(..., description="Array of todo items")


class SlashCommandToolInput(BaseModel):
    """Input parameters for the SlashCommand tool."""

    command: str = Field(..., description="Slash command to execute with arguments")


class SkillToolInput(BaseModel):
    """Input parameters for the Skill tool."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    skill: str = Field(..., description="Name of the skill to invoke")


class QuestionOption(BaseModel):
    """An option for a question in AskUserQuestion."""

    label: str = Field(..., description="Option display text")
    description: str = Field(..., description="Option description")


class Question(BaseModel):
    """A question in AskUserQuestion."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    question: str = Field(..., description="The question text")
    header: str = Field(..., description="Short label for the question (max 12 chars)")
    multi_select: bool = Field(..., description="Allow multiple selections")
    options: list[QuestionOption] = Field(..., description="Array of options (2-4)")


class AskUserQuestionToolInput(BaseModel):
    """Input parameters for the AskUserQuestion tool."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    questions: list[Question] = Field(..., description="Array of questions (1-4)")


class EnterPlanModeToolInput(BaseModel):
    """Input parameters for the EnterPlanMode tool (no parameters)."""


class ExitPlanModeToolInput(BaseModel):
    """Input parameters for the ExitPlanMode tool (no parameters)."""


class PreToolUseInput(BaseModel):
    """Input schema for PreToolUse hooks (FR-H010).

    Fires before a tool is executed, allowing hooks to deny, allow, modify,
    or request confirmation for the operation.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["PreToolUse"] = Field(
        "PreToolUse", description="Always 'PreToolUse'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    tool_name: str = Field(..., description="Name of the tool being invoked")
    tool_input: dict[str, object] = Field(
        ..., description="Tool-specific input parameters"
    )
    tool_use_id: str = Field(
        ..., description="Unique identifier for this tool invocation"
    )


def is_pre_tool_use_hook(hook_input: BaseModel) -> TypeIs[PreToolUseInput]:
    """Type guard to check if hook_input is PreToolUseInput."""
    return isinstance(hook_input, PreToolUseInput)


class PostToolUseInput(BaseModel):
    """Input schema for PostToolUse hooks (FR-H020).

    Fires after a tool has executed, providing access to the tool's response
    for logging, analysis, or context injection.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["PostToolUse"] = Field(
        "PostToolUse", description="Always 'PostToolUse'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    tool_name: str = Field(..., description="Name of the tool that was invoked")
    tool_input: dict[str, object] = Field(
        ..., description="Tool-specific input parameters"
    )
    tool_response: dict[str, object] = Field(..., description="Tool execution result")
    tool_use_id: str = Field(
        ..., description="Unique identifier for this tool invocation"
    )


def is_post_tool_use_hook(hook_input: BaseModel) -> TypeIs[PostToolUseInput]:
    """Type guard to check if hook_input is PostToolUseInput."""
    return isinstance(hook_input, PostToolUseInput)


class UserPromptSubmitInput(BaseModel):
    """Input schema for UserPromptSubmit hooks (FR-H030).

    Fires when the user submits a prompt, before Claude processes it.
    Allows preprocessing, validation, or context injection.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["UserPromptSubmit"] = Field(
        "UserPromptSubmit", description="Always 'UserPromptSubmit'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    prompt: str = Field(..., description="The user's submitted prompt text")


def is_user_prompt_submit_hook(hook_input: BaseModel) -> TypeIs[UserPromptSubmitInput]:
    """Type guard to check if hook_input is UserPromptSubmitInput."""
    return isinstance(hook_input, UserPromptSubmitInput)


class PermissionRequestInput(BaseModel):
    """Input schema for PermissionRequest hooks (FR-H040).

    Fires when Claude requests user permission for an operation.
    Allows auto-approval or auto-rejection of operations.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["PermissionRequest"] = Field(
        "PermissionRequest", description="Always 'PermissionRequest'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    tool_name: str = Field(..., description="Name of the tool requesting permission")
    tool_input: dict[str, object] = Field(
        ..., description="Tool-specific input parameters"
    )
    tool_use_id: str = Field(
        ..., description="Unique identifier for this tool invocation"
    )


def is_permission_request_hook(hook_input: BaseModel) -> TypeIs[PermissionRequestInput]:
    """Type guard to check if hook_input is PermissionRequestInput."""
    return isinstance(hook_input, PermissionRequestInput)


class NotificationInput(BaseModel):
    """Input schema for Notification hooks (FR-H050).

    Fires when a notification is about to be shown to the user.
    Allows filtering or suppression of notifications.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["Notification"] = Field(
        "Notification", description="Always 'Notification'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    message: str = Field(..., description="The notification message content")
    notification_type: Literal[
        "permission_prompt", "idle_prompt", "auth_success", "elicitation_dialog"
    ] = Field(..., description="Type of notification")


def is_notification_hook(hook_input: BaseModel) -> TypeIs[NotificationInput]:
    """Type guard to check if hook_input is NotificationInput."""
    return isinstance(hook_input, NotificationInput)


class SessionStartInput(BaseModel):
    """Input schema for SessionStart hooks (FR-H060).

    Fires when a session begins. Enables session initialization logic
    such as logging, welcome messages, or context injection.
    """

    session_id: UUID = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: Path = Field(
        ..., description="File path to the session transcript"
    )
    hook_event_name: Literal["SessionStart"] = Field(
        "SessionStart", description="Always 'SessionStart'"
    )
    cwd: Path | None = Field(None, description="Current working directory")
    source: Literal["startup", "resume", "clear", "compact"] = Field(
        ..., description="How the session started"
    )


def is_session_start_hook(hook_input: BaseModel) -> TypeIs[SessionStartInput]:
    """Type guard to check if hook_input is SessionStartInput."""
    return isinstance(hook_input, SessionStartInput)


class SessionEndInput(BaseModel):
    """Input schema for SessionEnd hooks (FR-H070).

    Fires when a session ends. Enables cleanup logic and session summary logging.

    Note: permission_mode is optional because Claude Code may not always
    provide it in SessionEnd events.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: (
        Literal["default", "plan", "acceptEdits", "bypassPermissions"] | None
    ) = Field(None, description="Current permission mode (may not be provided)")
    hook_event_name: Literal["SessionEnd"] = Field(
        "SessionEnd", description="Always 'SessionEnd'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    reason: Literal["clear", "logout", "prompt_input_exit", "other"] = Field(
        ..., description="Why the session ended"
    )


def is_session_end_hook(hook_input: BaseModel) -> TypeIs[SessionEndInput]:
    """Type guard to check if hook_input is SessionEndInput."""
    return isinstance(hook_input, SessionEndInput)


class StopInput(BaseModel):
    """Input schema for Stop hooks (FR-H080).

    Fires when the user interrupts an operation (e.g., Ctrl+C or Escape).
    Enables cleanup or logging.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["Stop"] = Field("Stop", description="Always 'Stop'")
    cwd: str | None = Field(None, description="Current working directory")
    stop_hook_active: bool = Field(
        ..., description="Whether stop hooks are currently active"
    )


def is_stop_hook(hook_input: BaseModel) -> TypeIs[StopInput]:
    """Type guard to check if hook_input is StopInput."""
    return isinstance(hook_input, StopInput)


class SubagentStopInput(BaseModel):
    """Input schema for SubagentStop hooks (FR-H090).

    Fires when a subagent (spawned via Task tool) is stopped.
    Enables subagent-specific cleanup.
    """

    agent_id: str = Field(
        ..., description="Unique identifier for the subagent being stopped"
    )
    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["SubagentStop"] = Field(
        "SubagentStop", description="Always 'SubagentStop'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    stop_hook_active: bool = Field(
        ..., description="Whether stop hooks are currently active"
    )


def is_subagent_stop_hook(hook_input: BaseModel) -> TypeIs[SubagentStopInput]:
    """Type guard to check if hook_input is SubagentStopInput."""
    return isinstance(hook_input, SubagentStopInput)


class PreCompactInput(BaseModel):
    """Input schema for PreCompact hooks (FR-H100).

    Fires before memory compaction. Enables injection of critical context
    that must be preserved across compaction boundaries.
    """

    session_id: str = Field(
        ..., description="Unique identifier for the current session"
    )
    transcript_path: str = Field(..., description="File path to the session transcript")
    permission_mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"] = (
        Field(..., description="Current permission mode")
    )
    hook_event_name: Literal["PreCompact"] = Field(
        "PreCompact", description="Always 'PreCompact'"
    )
    cwd: str | None = Field(None, description="Current working directory")
    trigger: Literal["manual", "auto"] = Field(
        ..., description="What triggered compaction"
    )
    custom_instructions: str = Field(
        ..., description="User's custom compaction instructions (may be empty)"
    )


def is_pre_compact_hook(hook_input: BaseModel) -> TypeIs[PreCompactInput]:
    """Type guard to check if hook_input is PreCompactInput."""
    return isinstance(hook_input, PreCompactInput)


type HookInputT = (
    PreToolUseInput
    | PostToolUseInput
    | UserPromptSubmitInput
    | PermissionRequestInput
    | NotificationInput
    | SessionStartInput
    | SessionEndInput
    | StopInput
    | SubagentStopInput
    | PreCompactInput
)


HOOK_EVENT_TYPE_TO_MODEL: dict[str, type[HookInputT]] = {
    HookEventType.PRE_TOOL_USE: PreToolUseInput,
    HookEventType.POST_TOOL_USE: PostToolUseInput,
    HookEventType.USER_PROMPT_SUBMIT: UserPromptSubmitInput,
    HookEventType.PERMISSION_REQUEST: PermissionRequestInput,
    HookEventType.NOTIFICATION: NotificationInput,
    HookEventType.SESSION_START: SessionStartInput,
    HookEventType.SESSION_END: SessionEndInput,
    HookEventType.STOP: StopInput,
    HookEventType.SUBAGENT_STOP: SubagentStopInput,
    HookEventType.PRE_COMPACTION: PreCompactInput,
}
