"""Utilities for working with Claude Code slash commands."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SlashCommandFrontmatter(BaseModel):
    """Frontmatter schema for slash command metadata."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    name: str
    allowed_tools: str | None = Field(default=None, alias="allowed-tools")
    argument_hint: str | None = Field(default=None, alias="argument-hint")
    description: str | None = None
    disable_model_invocation: bool | None = Field(
        default=None, alias="disable-model-invocation"
    )
    model: str | None = None
