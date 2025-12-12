"""Pydantic models for template contexts."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class BaseTemplateContext(BaseModel):
    """Base context available to all templates.

    This context is automatically populated by the template system
    and merged with component-specific contexts.
    """

    today: date = Field(default_factory=date.today, description="Current date")
    author_name: str | None = Field(default=None, description="Author name")
    author_email: str | None = Field(default=None, description="Author email")
    tool_versions: dict[str, str | None] = Field(
        default_factory=dict, description="Detected tool versions"
    )


class SpecContext(BaseTemplateContext):
    """Context for specification templates.

    Extends BaseTemplateContext with spec-specific fields.
    """

    title: str = Field(..., min_length=1, description="Specification title")
    version: str = Field(default="1.0.0", description="Specification version")
    status: Literal["draft", "review", "approved", "deprecated"] = Field(
        default="draft", description="Specification status"
    )
