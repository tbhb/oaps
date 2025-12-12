"""Utilities for working with Claude Code subagents."""

from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SubagentModel(StrEnum):
    """Models available for subagents."""

    SONNET = "sonnet"
    HAIKU = "haiku"
    OPUS = "opus"
    INHERIT = "inherit"


class SubagentPermissionMode(StrEnum):
    """Permission modes for subagents."""

    ACCEPT_EDITS = "acceptEdits"
    BYPASS_PERMISSIONS = "bypassPermissions"
    DEFAULT = "default"
    IGNORE = "ignore"
    PLAN = "plan"


class SubagentFrontmatter(BaseModel):
    """Frontmatter schema for subagent metadata."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    description: str
    name: str
    tools: str | None = Field(default=None, alias="allowed-tools")
    argument_hint: str | None = Field(default=None, alias="argument-hint")
    model: str | None = None
    permission_mode: SubagentPermissionMode | None = Field(
        default=None, alias="permissionMode"
    )
    skills: str | None = None
