"""Ideas configuration model.

This module provides the IdeasConfiguration Pydantic model for ideas settings.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class IdeasConfiguration(BaseModel):
    """OAPS ideas configuration.

    Controls tag definitions and idea workflow settings.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    tags: dict[str, str] = Field(
        default_factory=lambda: {
            "productivity": "Ideas related to improving efficiency and workflows",
            "ai": "Ideas involving artificial intelligence or machine learning",
            "automation": "Ideas for automating manual processes",
            "tooling": "Developer tools and infrastructure",
            "ux": "User experience improvements",
            "architecture": "System design and architecture",
            "process": "Team processes and methodologies",
            "research": "Research directions and experiments",
        },
        description="Base tag definitions (name -> description).",
    )
    extend_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Project-specific tag overrides and additions.",
    )

    @property
    def all_tags(self) -> dict[str, str]:
        """Merged tags with extend_tags taking precedence.

        Returns:
            Combined dictionary of all tags.
        """
        return {**self.tags, **self.extend_tags}
