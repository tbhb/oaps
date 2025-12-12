"""Hook configuration models.

This module provides Pydantic models for hook rules including
priorities, actions, and the overall rule configuration structure.
"""

from enum import StrEnum
from pathlib import Path  # noqa: TC003
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class RulePriority(StrEnum):
    """Priority level for hook rules.

    Rules are evaluated in priority order: critical first, then high, medium, low.
    Within the same priority level, rules are evaluated in definition order.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HookRuleActionConfiguration(BaseModel):
    """OAPS hook rule action configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    type: Literal[
        "log",
        "python",
        "shell",
        "deny",
        "allow",
        "warn",
        "suggest",
        "inject",
        "modify",
        "transform",
    ]

    # Mutually-exclusive execution fields
    entrypoint: str | None = Field(
        default=None, description="Python entrypoint for the action."
    )
    command: str | None = Field(
        default=None, description="Command to run for the action."
    )
    script: str | None = Field(
        default=None, description="Script content to execute for the action."
    )

    # Permission action fields
    message: str | None = Field(
        default=None,
        description="Message template for permission actions. Supports ${var} syntax.",
    )
    interrupt: bool = Field(
        default=True,
        description="Whether to interrupt the agent loop on deny.",
    )

    # Feedback action fields
    level: Literal["debug", "info", "warning", "error"] | None = Field(
        default=None,
        description="Log level for log action.",
    )
    content: str | None = Field(
        default=None,
        description="Content to inject for inject action. Supports ${var} syntax.",
    )

    # Modify action fields
    field: str | None = Field(
        default=None,
        description="Target field path for modify action.",
    )
    operation: Literal["set", "append", "prepend", "replace"] | None = Field(
        default=None,
        description="Operation to perform for modify action.",
    )
    value: str | None = Field(
        default=None,
        description="New value or content for modify action. Supports ${var} syntax.",
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern for replace operation.",
    )

    cwd: Path | None = Field(
        default=None,
        description="Working directory for the action relative to CLAUDE_PROJECT_DIR.",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for the action.",
    )
    shell: str | None = Field(default=None, description="Interpreter to use.")
    stdin: Literal["none", "json"] | None = Field(
        default=None, description="Type of stdin input to provide to the action."
    )
    stderr: Literal["append_to_stdout", "ignore", "log"] | None = Field(
        default=None, description="How to handle stderr from the action."
    )
    stdout: Literal["append_stop_reason", "ignore", "log"] | None = Field(
        default=None, description="How to handle stdout from the action."
    )
    timeout_ms: int | None = Field(
        default=None, description="Timeout for the action in milliseconds."
    )


class HookRuleConfiguration(BaseModel):
    """OAPS hook rule configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    id: str = Field(..., description="Unique identifier for the hook rule.")
    priority: RulePriority = Field(
        default=RulePriority.MEDIUM, description="Priority level for rule evaluation."
    )

    actions: list[HookRuleActionConfiguration] = Field(
        default_factory=list, description="List of actions for the hook rule."
    )
    condition: str = Field(..., description="Condition to trigger the hook rule.")
    description: str | None = Field(
        default=None, description="Description of the hook rule."
    )
    enabled: bool = Field(default=True, description="Whether the hook rule is enabled.")
    events: set[
        Literal[
            "all",
            "pre_tool_use",
            "post_tool_use",
            "permission_request",
            "user_prompt_submit",
            "notification",
            "session_start",
            "session_end",
            "stop",
            "subagent_stop",
            "pre_compact",
        ]
    ] = Field(..., description="The hook events to which this rule applies.")
    result: Literal["block", "ok", "warn"] = Field(
        ...,
        description="Type of action to perform when the hook rule matches.",
    )
    terminal: bool = Field(
        default=False,
        description="Whether to stop processing further rules if this rule matches.",
    )

    # Source tracking field (set by loader, not user-specified)
    source_file: Path | None = Field(
        default=None,
        description="Path to the file this rule was loaded from (for debugging).",
    )


class HooksConfiguration(BaseModel):
    """OAPS hooks configuration.

    Attributes:
        log_level: Log level for hook execution logging.
        log_max_bytes: Maximum size of hooks.log in bytes before rotation.
        log_backup_count: Number of rotated log files to keep.
        rules: List of hook rules defining event handlers.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    log_level: Literal["error", "warning", "info", "debug"] = Field(
        default="info",
        description="Log level for hook execution logging.",
    )
    log_max_bytes: int | None = Field(
        default=None,
        description=(
            "Maximum size of hooks.log in bytes before rotation "
            "(e.g., 10000000 for 10MB). "
            "Must be set together with log_backup_count for rotation to be enabled."
        ),
    )
    log_backup_count: int | None = Field(
        default=None,
        description=(
            "Number of rotated log files to keep "
            "(e.g., 5 for hooks.log.1 through hooks.log.5). "
            "Must be set together with log_max_bytes for rotation to be enabled."
        ),
    )
    rules: list[HookRuleConfiguration] = Field(
        default_factory=list,
        description="List of hook rules.",
    )
