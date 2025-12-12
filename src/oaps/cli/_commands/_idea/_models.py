"""Data models for idea documents."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypedDict


class IdeaStatus(StrEnum):
    """Status values for idea documents."""

    SEED = "seed"
    EXPLORING = "exploring"
    REFINING = "refining"
    CRYSTALLIZED = "crystallized"
    ARCHIVED = "archived"


class IdeaType(StrEnum):
    """Type values for idea documents."""

    TECHNICAL = "technical"
    PRODUCT = "product"
    PROCESS = "process"
    RESEARCH = "research"


# Status emoji mapping
STATUS_EMOJI: dict[IdeaStatus, str] = {
    IdeaStatus.SEED: "🌱",
    IdeaStatus.EXPLORING: "🔍",
    IdeaStatus.REFINING: "🔄",
    IdeaStatus.CRYSTALLIZED: "💎",
    IdeaStatus.ARCHIVED: "📦",
}


class IdeaReference(TypedDict, total=False):
    """External reference in idea frontmatter."""

    url: str
    title: str


class IdeaWorkflowState(TypedDict, total=False):
    """Workflow state in idea frontmatter."""

    phase: str
    iteration: int


@dataclass(frozen=True, slots=True)
class IdeaFrontmatter:
    """Parsed idea document frontmatter."""

    id: str
    title: str
    status: IdeaStatus
    type: IdeaType
    created: str
    updated: str
    author: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    related_ideas: tuple[str, ...] = field(default_factory=tuple)
    references: tuple[IdeaReference, ...] = field(default_factory=tuple)
    workflow: IdeaWorkflowState | None = None


@dataclass(frozen=True, slots=True)
class IdeaIndexEntry:
    """Entry in ideas/index.json."""

    id: str
    title: str
    status: str
    type: str
    tags: tuple[str, ...]
    file_path: str
    created: str
    updated: str
    author: str | None = None
