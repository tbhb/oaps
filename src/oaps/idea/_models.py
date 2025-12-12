"""Data models for the idea management system.

This module provides the core data models for ideas, including the full Idea
dataclass and the lightweight IdeaSummary for index listings. It re-exports
common types from the commands layer for convenience.
"""

from dataclasses import dataclass, field
from datetime import datetime

# Re-export types from commands layer for convenience
from oaps.cli._commands._idea._models import (
    IdeaReference,
    IdeaStatus,
    IdeaType,
    IdeaWorkflowState,
)

__all__ = [
    "Idea",
    "IdeaReference",
    "IdeaStatus",
    "IdeaSummary",
    "IdeaType",
    "IdeaWorkflowState",
]


@dataclass(frozen=True, slots=True)
class IdeaSummary:
    """Lightweight idea representation for index listings.

    Contains only the essential fields needed for displaying ideas in
    lists and performing filtering operations without loading full content.

    Attributes:
        id: Unique idea identifier (format: YYYYMMDD-HHMMSS-slug).
        title: Human-readable idea title.
        status: Current workflow status.
        idea_type: Category of the idea.
        created: When the idea was created.
        updated: When the idea was last modified.
        tags: Freeform tags for filtering.
        author: Creator of the idea.
        file_path: Relative path to the idea file from ideas directory.
    """

    id: str
    title: str
    status: IdeaStatus
    idea_type: IdeaType
    created: datetime
    updated: datetime
    tags: tuple[str, ...] = field(default_factory=tuple)
    author: str | None = None
    file_path: str = ""


@dataclass(frozen=True, slots=True)
class Idea:
    """Complete idea representation with full metadata and body content.

    This is the full idea dataclass containing all metadata and the
    markdown body content. Used when reading or writing individual ideas.

    Attributes:
        id: Unique idea identifier (format: YYYYMMDD-HHMMSS-slug).
        title: Human-readable idea title.
        status: Current workflow status.
        idea_type: Category of the idea.
        created: When the idea was created.
        updated: When the idea was last modified.
        body: Markdown content of the idea.
        tags: Freeform tags for filtering.
        author: Creator of the idea.
        related_ideas: IDs of related ideas.
        references: External references (URLs with titles).
        workflow: Optional workflow state tracking.
        file_path: Relative path to the idea file from ideas directory.
    """

    id: str
    title: str
    status: IdeaStatus
    idea_type: IdeaType
    created: datetime
    updated: datetime
    body: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    author: str | None = None
    related_ideas: tuple[str, ...] = field(default_factory=tuple)
    references: tuple[IdeaReference, ...] = field(default_factory=tuple)
    workflow: IdeaWorkflowState | None = None
    file_path: str = ""

    def to_summary(self) -> IdeaSummary:
        """Convert this idea to a lightweight summary.

        Returns:
            IdeaSummary containing only essential fields.
        """
        return IdeaSummary(
            id=self.id,
            title=self.title,
            status=self.status,
            idea_type=self.idea_type,
            created=self.created,
            updated=self.updated,
            tags=self.tags,
            author=self.author,
            file_path=self.file_path,
        )
