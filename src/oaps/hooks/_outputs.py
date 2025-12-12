"""Pydantic models for Claude Code hook outputs."""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PreToolUseHookSpecificOutput(BaseModel):
    """Hook-specific output for PreToolUse hooks.

    Supports deny, allow, ask, and modify decisions.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    hook_event_name: Literal["PreToolUse"] = Field(
        default="PreToolUse", description="Must be 'PreToolUse'"
    )
    permission_decision: Literal["deny", "allow", "ask"] | None = Field(
        default=None, description="Permission decision: 'deny', 'allow', or 'ask'"
    )
    permission_decision_reason: str | None = Field(
        default=None, description="Human-readable reason for deny or ask decisions"
    )
    updated_input: dict[str, object] | None = Field(
        default=None,
        description="Modified tool input to use instead (for modify action)",
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PostToolUseHookSpecificOutput(BaseModel):
    """Hook-specific output for PostToolUse hooks.

    Supports context injection after tool execution.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    hook_event_name: Literal["PostToolUse"] = Field(
        default="PostToolUse", description="Must be 'PostToolUse'"
    )
    additional_context: str | None = Field(
        default=None, description="Context to add to the conversation"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class UserPromptSubmitHookSpecificOutput(BaseModel):
    """Hook-specific output for UserPromptSubmit hooks.

    Supports context injection before Claude processes the prompt.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    hook_event_name: Literal["UserPromptSubmit"] = Field(
        default="UserPromptSubmit", description="Must be 'UserPromptSubmit'"
    )
    additional_context: str | None = Field(
        default=None, description="Context injected before Claude sees prompt"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PermissionRequestDecision(BaseModel):
    """Decision structure for PermissionRequest hooks."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    behavior: Literal["allow", "deny"] = Field(
        default=..., description="Permission behavior: 'allow' or 'deny'"
    )
    updated_input: dict[str, object] | None = Field(
        default=None, description="Modified tool input (for allow with modification)"
    )
    message: str | None = Field(None, description="Denial message (for deny)")
    interrupt: bool | None = Field(
        default=None, description="Whether to interrupt the agent loop (for deny)"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PermissionRequestHookSpecificOutput(BaseModel):
    """Hook-specific output for PermissionRequest hooks.

    Supports auto-approval and auto-rejection of permission requests.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    hook_event_name: Literal["PermissionRequest"] = Field(
        default="PermissionRequest", description="Must be 'PermissionRequest'"
    )
    decision: PermissionRequestDecision = Field(
        default=..., description="The permission decision"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class SessionStartHookSpecificOutput(BaseModel):
    """Hook-specific output for SessionStart hooks.

    Supports context injection at session start.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    hook_event_name: Literal["SessionStart"] = Field(
        default="SessionStart", description="Must be 'SessionStart'"
    )
    additional_context: str | None = Field(
        default=None, description="Context to inject at session start"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PreCompactHookSpecificOutput(BaseModel):
    """Hook-specific output for PreCompact hooks.

    Supports context injection to preserve information across compaction.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    hook_event_name: Literal["PreCompact"] = Field(
        default="PreCompact", description="Must be 'PreCompact'"
    )
    additional_context: str | None = Field(
        default=None, description="Context to inject into compaction"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PreToolUseOutput(BaseModel):
    """Output schema for PreToolUse hooks.

    Supports deny, allow, ask, and modify decisions for tool invocations.
    An empty response or exit code 0 without output allows the operation.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: PreToolUseHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PostToolUseOutput(BaseModel):
    """Output schema for PostToolUse hooks.

    Supports blocking further processing and context injection.
    An empty response allows processing to continue.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    decision: Literal["block"] | None = Field(
        default=None, description="Set to 'block' to prevent further processing"
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Human-readable reason for blocking (required when decision is 'block')"
        ),
    )
    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: PostToolUseHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class UserPromptSubmitOutput(BaseModel):
    """Output schema for UserPromptSubmit hooks.

    Supports blocking prompts and context injection.
    An empty response allows the prompt to be processed.
    Plain text stdout is also valid and added as context.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    decision: Literal["block"] | None = Field(
        default=None, description="Set to 'block' to prevent prompt processing"
    )
    reason: str | None = Field(
        default=None, description="Reason shown to user (required when blocking)"
    )
    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: UserPromptSubmitHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PermissionRequestOutput(BaseModel):
    """Output schema for PermissionRequest hooks.

    Supports auto-approval and auto-rejection of permission requests.
    An empty response shows the standard permission dialog.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: PermissionRequestHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class NotificationOutput(BaseModel):
    """Output schema for Notification hooks.

    Supports suppression of notifications.
    An empty response shows the notification normally.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue processing (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Whether to suppress the notification display"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class SessionStartOutput(BaseModel):
    """Output schema for SessionStart hooks.

    Supports context injection at session start.
    An empty response continues with normal session startup.
    Plain text stdout is also valid and added as context.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: SessionStartHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class SessionEndOutput(BaseModel):
    """Output schema for SessionEnd hooks.

    SessionEnd produces no meaningful output. Any output is logged
    but does not affect behavior since the session is already ending.
    """

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class StopOutput(BaseModel):
    """Output schema for Stop hooks.

    Supports blocking the stop operation.
    An empty response allows the stop to proceed.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    decision: Literal["block"] | None = Field(
        default=None, description="Set to 'block' to prevent the stop"
    )
    reason: str | None = Field(
        default=None, description="Reason shown to user (required when blocking)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class SubagentStopOutput(BaseModel):
    """Output schema for SubagentStop hooks.

    Supports blocking the subagent stop operation.
    An empty response allows the subagent stop to proceed.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True
    )

    decision: Literal["block"] | None = Field(
        default=None, description="Set to 'block' to prevent the subagent stop"
    )
    reason: str | None = Field(
        default=None, description="Reason shown to user (required when blocking)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)


class PreCompactOutput(BaseModel):
    """Output schema for PreCompact hooks.

    Supports context injection to preserve information across compaction.
    An empty response proceeds with default compaction behavior.
    Plain text stdout is also valid and added to compaction context.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, arbitrary_types_allowed=True
    )

    continue_: bool | None = Field(
        default=None,
        alias="continue",
        description="Whether to continue execution (default: true)",
    )
    stop_reason: str | None = Field(
        default=None, description="Message displayed when continue is false"
    )
    suppress_output: bool | None = Field(
        default=None, description="Hide stdout from transcript (default: false)"
    )
    system_message: str | None = Field(
        default=None, description="Warning message shown to user"
    )
    hook_specific_output: PreCompactHookSpecificOutput | None = Field(
        default=None, description="Hook-specific output data"
    )

    def to_output_json(self) -> str:
        """Serialize to JSON string with camelCase keys."""
        return self.model_dump_json(by_alias=True, exclude_none=True)
