"""Input builders with fluent API for hook testing.

Provides builder classes for each hook input type with sensible defaults
and convenience methods for common scenarios.
"""

from pathlib import Path
from typing import Literal, Self
from uuid import UUID, uuid4

from oaps.hooks._inputs import (
    NotificationInput,
    PermissionRequestInput,
    PostToolUseInput,
    PreCompactInput,
    PreToolUseInput,
    SessionEndInput,
    SessionStartInput,
    StopInput,
    SubagentStopInput,
    UserPromptSubmitInput,
)

# Default transcript path - using a non-tmp path for test defaults
_DEFAULT_TRANSCRIPT_PATH = "/test/transcript.json"


class PreToolUseInputBuilder:
    """Fluent builder for PreToolUseInput with common tool configurations."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._tool_name: str = "Bash"
        self._tool_input: dict[str, object] = {"command": "echo hello"}
        self._tool_use_id: str = "tool-123"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_tool_name(self, name: str) -> Self:
        self._tool_name = name
        return self

    def with_tool_input(self, tool_input: dict[str, object]) -> Self:
        self._tool_input = tool_input
        return self

    def with_tool_use_id(self, tool_use_id: str) -> Self:
        self._tool_use_id = tool_use_id
        return self

    # Convenience methods for common tool configurations

    def with_bash_command(self, command: str, description: str | None = None) -> Self:
        self._tool_name = "Bash"
        self._tool_input = {"command": command}
        if description is not None:
            self._tool_input["description"] = description
        return self

    def with_read_file(
        self, file_path: str, offset: int | None = None, limit: int | None = None
    ) -> Self:
        self._tool_name = "Read"
        self._tool_input = {"file_path": file_path}
        if offset is not None:
            self._tool_input["offset"] = offset
        if limit is not None:
            self._tool_input["limit"] = limit
        return self

    def with_write_file(self, file_path: str, content: str) -> Self:
        self._tool_name = "Write"
        self._tool_input = {"file_path": file_path, "content": content}
        return self

    def with_edit_file(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        *,
        replace_all: bool = False,
    ) -> Self:
        self._tool_name = "Edit"
        self._tool_input = {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
            "replace_all": replace_all,
        }
        return self

    def with_glob(self, pattern: str, path: str | None = None) -> Self:
        self._tool_name = "Glob"
        self._tool_input = {"pattern": pattern}
        if path is not None:
            self._tool_input["path"] = path
        return self

    def with_grep(self, pattern: str, path: str | None = None) -> Self:
        self._tool_name = "Grep"
        self._tool_input = {"pattern": pattern}
        if path is not None:
            self._tool_input["path"] = path
        return self

    def with_web_fetch(self, url: str, prompt: str) -> Self:
        self._tool_name = "WebFetch"
        self._tool_input = {"url": url, "prompt": prompt}
        return self

    def with_web_search(self, query: str) -> Self:
        self._tool_name = "WebSearch"
        self._tool_input = {"query": query}
        return self

    def with_task(self, prompt: str, subagent_type: str | None = None) -> Self:
        self._tool_name = "Task"
        self._tool_input = {"prompt": prompt}
        if subagent_type is not None:
            self._tool_input["subagent_type"] = subagent_type
        return self

    def with_notebook_edit(
        self, notebook_path: str, new_source: str, cell_id: str | None = None
    ) -> Self:
        self._tool_name = "NotebookEdit"
        self._tool_input = {"notebook_path": notebook_path, "new_source": new_source}
        if cell_id is not None:
            self._tool_input["cell_id"] = cell_id
        return self

    def build(self) -> PreToolUseInput:
        return PreToolUseInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="PreToolUse",
            cwd=self._cwd,
            tool_name=self._tool_name,
            tool_input=self._tool_input,
            tool_use_id=self._tool_use_id,
        )


class PostToolUseInputBuilder:
    """Fluent builder for PostToolUseInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._tool_name: str = "Bash"
        self._tool_input: dict[str, object] = {"command": "echo hello"}
        self._tool_response: dict[str, object] = {"output": "hello\n", "exit_code": 0}
        self._tool_use_id: str = "tool-123"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_tool_name(self, name: str) -> Self:
        self._tool_name = name
        return self

    def with_tool_input(self, tool_input: dict[str, object]) -> Self:
        self._tool_input = tool_input
        return self

    def with_tool_response(self, tool_response: dict[str, object]) -> Self:
        self._tool_response = tool_response
        return self

    def with_tool_use_id(self, tool_use_id: str) -> Self:
        self._tool_use_id = tool_use_id
        return self

    # Convenience methods

    def with_bash_result(
        self,
        command: str,
        output: str,
        exit_code: int = 0,
        error: str | None = None,
    ) -> Self:
        self._tool_name = "Bash"
        self._tool_input = {"command": command}
        self._tool_response = {"output": output, "exit_code": exit_code}
        if error is not None:
            self._tool_response["error"] = error
        return self

    def with_read_result(self, file_path: str, content: str) -> Self:
        self._tool_name = "Read"
        self._tool_input = {"file_path": file_path}
        self._tool_response = {"content": content}
        return self

    def with_write_result(self, file_path: str, *, success: bool = True) -> Self:
        self._tool_name = "Write"
        self._tool_input = {"file_path": file_path, "content": "..."}
        self._tool_response = {"success": success}
        return self

    def with_error_response(self, error: str) -> Self:
        self._tool_response = {"error": error}
        return self

    def build(self) -> PostToolUseInput:
        return PostToolUseInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="PostToolUse",
            cwd=self._cwd,
            tool_name=self._tool_name,
            tool_input=self._tool_input,
            tool_response=self._tool_response,
            tool_use_id=self._tool_use_id,
        )


class UserPromptSubmitInputBuilder:
    """Fluent builder for UserPromptSubmitInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._prompt: str = "hello"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_prompt(self, prompt: str) -> Self:
        self._prompt = prompt
        return self

    def build(self) -> UserPromptSubmitInput:
        return UserPromptSubmitInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="UserPromptSubmit",
            cwd=self._cwd,
            prompt=self._prompt,
        )


class PermissionRequestInputBuilder:
    """Fluent builder for PermissionRequestInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._tool_name: str = "Bash"
        self._tool_input: dict[str, object] = {"command": "rm -rf /"}
        self._tool_use_id: str = "tool-123"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_tool_name(self, name: str) -> Self:
        self._tool_name = name
        return self

    def with_tool_input(self, tool_input: dict[str, object]) -> Self:
        self._tool_input = tool_input
        return self

    def with_tool_use_id(self, tool_use_id: str) -> Self:
        self._tool_use_id = tool_use_id
        return self

    def with_bash_command(self, command: str) -> Self:
        self._tool_name = "Bash"
        self._tool_input = {"command": command}
        return self

    def build(self) -> PermissionRequestInput:
        return PermissionRequestInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="PermissionRequest",
            cwd=self._cwd,
            tool_name=self._tool_name,
            tool_input=self._tool_input,
            tool_use_id=self._tool_use_id,
        )


class NotificationInputBuilder:
    """Fluent builder for NotificationInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._message: str = "Notification message"
        self._notification_type: Literal[
            "permission_prompt", "idle_prompt", "auth_success", "elicitation_dialog"
        ] = "permission_prompt"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_message(self, message: str) -> Self:
        self._message = message
        return self

    def with_notification_type(
        self,
        notification_type: Literal[
            "permission_prompt", "idle_prompt", "auth_success", "elicitation_dialog"
        ],
    ) -> Self:
        self._notification_type = notification_type
        return self

    def build(self) -> NotificationInput:
        return NotificationInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="Notification",
            cwd=self._cwd,
            message=self._message,
            notification_type=self._notification_type,
        )


class SessionStartInputBuilder:
    """Fluent builder for SessionStartInput."""

    def __init__(self) -> None:
        self._session_id: UUID = uuid4()
        self._transcript_path: Path = Path(_DEFAULT_TRANSCRIPT_PATH)
        self._cwd: Path | None = Path("/home/user/project")
        self._source: Literal["startup", "resume", "clear", "compact"] = "startup"

    def with_session_id(self, session_id: UUID) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: Path) -> Self:
        self._transcript_path = path
        return self

    def with_cwd(self, cwd: Path | None) -> Self:
        self._cwd = cwd
        return self

    def with_source(
        self, source: Literal["startup", "resume", "clear", "compact"]
    ) -> Self:
        self._source = source
        return self

    def build(self) -> SessionStartInput:
        return SessionStartInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            hook_event_name="SessionStart",
            cwd=self._cwd,
            source=self._source,
        )


class SessionEndInputBuilder:
    """Fluent builder for SessionEndInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._reason: Literal["clear", "logout", "prompt_input_exit", "other"] = "other"

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_reason(
        self, reason: Literal["clear", "logout", "prompt_input_exit", "other"]
    ) -> Self:
        self._reason = reason
        return self

    def build(self) -> SessionEndInput:
        return SessionEndInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="SessionEnd",
            cwd=self._cwd,
            reason=self._reason,
        )


class StopInputBuilder:
    """Fluent builder for StopInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._stop_hook_active: bool = False

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_stop_hook_active(self, active: bool) -> Self:
        self._stop_hook_active = active
        return self

    def build(self) -> StopInput:
        return StopInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="Stop",
            cwd=self._cwd,
            stop_hook_active=self._stop_hook_active,
        )


class SubagentStopInputBuilder:
    """Fluent builder for SubagentStopInput."""

    def __init__(self) -> None:
        self._agent_id: str = "test-agent"
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._stop_hook_active: bool = False

    def with_agent_id(self, agent_id: str) -> Self:
        self._agent_id = agent_id
        return self

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_stop_hook_active(self, active: bool) -> Self:
        self._stop_hook_active = active
        return self

    def build(self) -> SubagentStopInput:
        return SubagentStopInput(
            agent_id=self._agent_id,
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="SubagentStop",
            cwd=self._cwd,
            stop_hook_active=self._stop_hook_active,
        )


class PreCompactInputBuilder:
    """Fluent builder for PreCompactInput."""

    def __init__(self) -> None:
        self._session_id: str = "test-session"
        self._transcript_path: str = _DEFAULT_TRANSCRIPT_PATH
        self._permission_mode: Literal[
            "default", "plan", "acceptEdits", "bypassPermissions"
        ] = "default"
        self._cwd: str | None = "/home/user/project"
        self._trigger: Literal["manual", "auto"] = "auto"
        self._custom_instructions: str = ""

    def with_session_id(self, session_id: str) -> Self:
        self._session_id = session_id
        return self

    def with_transcript_path(self, path: str) -> Self:
        self._transcript_path = path
        return self

    def with_permission_mode(
        self, mode: Literal["default", "plan", "acceptEdits", "bypassPermissions"]
    ) -> Self:
        self._permission_mode = mode
        return self

    def with_cwd(self, cwd: str | None) -> Self:
        self._cwd = cwd
        return self

    def with_trigger(self, trigger: Literal["manual", "auto"]) -> Self:
        self._trigger = trigger
        return self

    def with_custom_instructions(self, instructions: str) -> Self:
        self._custom_instructions = instructions
        return self

    def build(self) -> PreCompactInput:
        return PreCompactInput(
            session_id=self._session_id,
            transcript_path=self._transcript_path,
            permission_mode=self._permission_mode,
            hook_event_name="PreCompact",
            cwd=self._cwd,
            trigger=self._trigger,
            custom_instructions=self._custom_instructions,
        )


# Type alias for all input builders
type InputBuilder = (
    PreToolUseInputBuilder
    | PostToolUseInputBuilder
    | UserPromptSubmitInputBuilder
    | PermissionRequestInputBuilder
    | NotificationInputBuilder
    | SessionStartInputBuilder
    | SessionEndInputBuilder
    | StopInputBuilder
    | SubagentStopInputBuilder
    | PreCompactInputBuilder
)


def create_input(input_type: str) -> InputBuilder:
    """Factory function to create an input builder by event type name.

    Args:
        input_type: The event type name (e.g., "pre_tool_use", "post_tool_use").

    Returns:
        An appropriate input builder instance.

    Raises:
        ValueError: If input_type is not recognized.
    """
    builders: dict[str, type[InputBuilder]] = {
        "pre_tool_use": PreToolUseInputBuilder,
        "post_tool_use": PostToolUseInputBuilder,
        "user_prompt_submit": UserPromptSubmitInputBuilder,
        "permission_request": PermissionRequestInputBuilder,
        "notification": NotificationInputBuilder,
        "session_start": SessionStartInputBuilder,
        "session_end": SessionEndInputBuilder,
        "stop": StopInputBuilder,
        "subagent_stop": SubagentStopInputBuilder,
        "pre_compact": PreCompactInputBuilder,
    }

    builder_class = builders.get(input_type)
    if builder_class is None:
        msg = f"Unknown input type: {input_type}"
        raise ValueError(msg)
    return builder_class()
