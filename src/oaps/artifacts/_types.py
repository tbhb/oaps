"""Data classes and type definitions for the artifact system.

This module defines the core data structures used throughout the artifact system:
- TypeField and TypeDefinition for artifact type specifications
- ArtifactMetadata and Artifact for artifact data
- ValidationError for validation results
- BASE_TYPES tuple containing all 10 base artifact types
"""

from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 - needed at runtime for slots dataclass
from pathlib import Path  # noqa: TC003 - needed at runtime for slots dataclass
from typing import Any, Literal

# Placeholder - will be fully implemented in Task 1.2 and 1.3


@dataclass(frozen=True, slots=True)
class TypeField:
    """Definition of a type-specific metadata field.

    Attributes:
        name: Field name in metadata.
        field_type: Type of the field (string, integer, boolean, date, array, object).
        description: Brief description of the field's purpose.
        required: Whether this field is required for the artifact type.
        allowed_values: Optional tuple of allowed values for enum-like fields.
    """

    name: str
    field_type: str
    description: str
    required: bool = False
    allowed_values: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class TypeDefinition:
    """Definition of an artifact type.

    Attributes:
        prefix: Two-letter prefix (e.g., "RV" for Review).
        name: Human-readable name (e.g., "review").
        description: Brief description of the artifact type.
        category: Storage category - "text" or "binary".
        subtypes: Allowed subtypes for this artifact type.
        type_fields: Type-specific metadata fields.
        formats: Allowed file formats (binary types only).
        template: Path to structural template (text types only).
    """

    prefix: str
    name: str
    description: str
    category: Literal["text", "binary"]
    subtypes: tuple[str, ...] = ()
    type_fields: tuple[TypeField, ...] = ()
    formats: tuple[str, ...] = ()
    template: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    """Parsed artifact metadata from frontmatter or sidecar file.

    Attributes:
        id: Artifact identifier (e.g., "RV-0001").
        type: Artifact type name (e.g., "review").
        title: Human-readable title.
        status: Artifact status (draft, complete, superseded, retracted).
        created: Creation timestamp.
        author: Creator identifier.
        subtype: Further categorization within type.
        updated: Last modification timestamp.
        reviewers: Who reviewed/approved this artifact.
        references: IDs of related requirements, tests, or artifacts.
        supersedes: Artifact ID this replaces.
        superseded_by: Artifact ID that replaced this.
        tags: Freeform tags for filtering.
        summary: Brief description for listings.
        type_fields: Type-specific metadata fields.
    """

    id: str
    type: str
    title: str
    status: str
    created: datetime
    author: str
    subtype: str | None = None
    updated: datetime | None = None
    reviewers: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    supersedes: str | None = None
    superseded_by: str | None = None
    tags: tuple[str, ...] = ()
    summary: str | None = None
    type_fields: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportExplicitAny]


@dataclass(frozen=True, slots=True)
class Artifact:
    """Represents an artifact with metadata and file information.

    Attributes:
        id: Artifact identifier (e.g., "RV-0001").
        type: Artifact type name (e.g., "review").
        title: Human-readable title.
        status: Artifact status (draft, complete, superseded, retracted).
        created: Creation timestamp.
        author: Creator identifier.
        file_path: Path to the artifact file.
        subtype: Further categorization within type.
        updated: Last modification timestamp.
        reviewers: Who reviewed/approved this artifact.
        references: IDs of related requirements, tests, or artifacts.
        supersedes: Artifact ID this replaces.
        superseded_by: Artifact ID that replaced this.
        tags: Freeform tags for filtering.
        summary: Brief description for listings.
        metadata_file_path: Path to sidecar metadata (binary artifacts only).
        type_fields: Type-specific metadata fields.
    """

    id: str
    type: str
    title: str
    status: str
    created: datetime
    author: str
    file_path: Path
    subtype: str | None = None
    updated: datetime | None = None
    reviewers: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    supersedes: str | None = None
    superseded_by: str | None = None
    tags: tuple[str, ...] = ()
    summary: str | None = None
    metadata_file_path: Path | None = None
    type_fields: dict[str, Any] = field(default_factory=dict)  # pyright: ignore[reportExplicitAny]

    @property
    def is_binary(self) -> bool:
        """Whether this is a binary artifact (has sidecar metadata)."""
        return self.metadata_file_path is not None

    @property
    def is_text(self) -> bool:
        """Whether this is a text artifact (has embedded frontmatter)."""
        return self.metadata_file_path is None

    @property
    def prefix(self) -> str:
        """Extract prefix from ID (e.g., 'RV' from 'RV-0001')."""
        return self.id.split("-")[0]

    @property
    def number(self) -> int:
        """Extract number from ID (e.g., 1 from 'RV-0001')."""
        return int(self.id.split("-")[1])


@dataclass(frozen=True, slots=True)
class ValidationError:
    """Validation error or warning.

    Attributes:
        level: Severity level ("error" or "warning").
        message: Human-readable error message.
        artifact_id: ID of the artifact with the error (if applicable).
        field: Name of the field with the error (if applicable).
    """

    level: Literal["error", "warning"]
    message: str
    artifact_id: str | None = None
    field: str | None = None


# =============================================================================
# Base Type Definitions
# =============================================================================

# Review (RV) - Formal examination of specifications or implementations
_REVIEW_TYPE = TypeDefinition(
    prefix="RV",
    name="review",
    description="Formal examination of a work product",
    category="text",
    subtypes=("design", "security", "accessibility", "peer", "external", "code"),
    type_fields=(
        TypeField(
            name="review_type",
            field_type="string",
            description="Type of review",
            required=True,
            allowed_values=(
                "design",
                "security",
                "accessibility",
                "peer",
                "external",
                "code",
            ),
        ),
        TypeField(
            name="findings",
            field_type="integer",
            description="Number of findings",
        ),
        TypeField(
            name="severity",
            field_type="string",
            description="Highest severity",
            allowed_values=("critical", "high", "medium", "low", "info"),
        ),
        TypeField(
            name="remediation_status",
            field_type="string",
            description="Remediation status",
            allowed_values=("pending", "in_progress", "complete"),
        ),
    ),
    template="review.md",
)

# Decision (DC) - Choices made during development (ADR-style)
_DECISION_TYPE = TypeDefinition(
    prefix="DC",
    name="decision",
    description="Documented choice made during development",
    category="text",
    subtypes=("architecture", "design", "process", "tradeoff", "technology"),
    type_fields=(
        TypeField(
            name="decision_status",
            field_type="string",
            description="Decision status",
            allowed_values=("proposed", "accepted", "rejected", "deprecated"),
        ),
        TypeField(
            name="decision_date",
            field_type="date",
            description="When decision was made",
        ),
        TypeField(
            name="alternatives_considered",
            field_type="integer",
            description="Number of alternatives evaluated",
        ),
        TypeField(
            name="decision_drivers",
            field_type="array",
            description="Key factors driving the decision",
        ),
    ),
    template="decision.md",
)

# Analysis (AN) - Detailed examination of specific aspects
_ANALYSIS_TYPE = TypeDefinition(
    prefix="AN",
    name="analysis",
    description="Detailed examination of specific aspects",
    category="text",
    subtypes=("impact", "feasibility", "risk", "compliance", "gap", "performance"),
    type_fields=(
        TypeField(
            name="analysis_type",
            field_type="string",
            description="Type of analysis",
            allowed_values=(
                "impact",
                "feasibility",
                "risk",
                "compliance",
                "gap",
                "performance",
            ),
        ),
        TypeField(
            name="scope",
            field_type="string",
            description="What the analysis covers",
        ),
        TypeField(
            name="conclusion",
            field_type="string",
            description="Summary conclusion",
        ),
    ),
    template="analysis.md",
)

# Report (RP) - Completion status, summaries, periodic documentation
_REPORT_TYPE = TypeDefinition(
    prefix="RP",
    name="report",
    description="Completion status, summaries, and periodic documentation",
    category="text",
    subtypes=("completion", "status", "summary", "post-mortem", "metrics"),
    type_fields=(
        TypeField(
            name="report_type",
            field_type="string",
            description="Type of report",
            allowed_values=(
                "completion",
                "status",
                "summary",
                "post-mortem",
                "metrics",
            ),
        ),
        TypeField(
            name="period_start",
            field_type="date",
            description="Start of reporting period",
        ),
        TypeField(
            name="period_end",
            field_type="date",
            description="End of reporting period",
        ),
        TypeField(
            name="metrics",
            field_type="object",
            description="Key metrics as name-value pairs",
        ),
    ),
    template="report.md",
)

# Example (EX) - Sample implementations, code snippets, worked examples
_EXAMPLE_TYPE = TypeDefinition(
    prefix="EX",
    name="example",
    description="Sample implementations and worked examples",
    category="text",
    subtypes=("implementation", "snippet", "config", "api", "test", "workflow"),
    type_fields=(
        TypeField(
            name="example_type",
            field_type="string",
            description="Type of example",
            allowed_values=(
                "implementation",
                "snippet",
                "config",
                "api",
                "test",
                "workflow",
            ),
        ),
        TypeField(
            name="language",
            field_type="string",
            description="Programming language",
        ),
        TypeField(
            name="runtime",
            field_type="string",
            description="Runtime/framework if applicable",
        ),
        TypeField(
            name="tested",
            field_type="boolean",
            description="Whether example has been verified",
        ),
    ),
    template="example.md",
)

# Change (CH) - Modifications to approved specifications or released content
_CHANGE_TYPE = TypeDefinition(
    prefix="CH",
    name="change",
    description="Modifications to approved specifications or released content",
    category="text",
    subtypes=("erratum", "amendment", "clarification", "deprecation"),
    type_fields=(
        TypeField(
            name="change_type",
            field_type="string",
            description="Type of change",
            required=True,
            allowed_values=("erratum", "amendment", "clarification", "deprecation"),
        ),
        TypeField(
            name="affected_items",
            field_type="array",
            description="IDs of affected requirements, tests, or artifacts",
        ),
        TypeField(
            name="effective_date",
            field_type="date",
            description="When change becomes effective",
        ),
        TypeField(
            name="breaking",
            field_type="boolean",
            description="Whether this is a breaking change",
        ),
    ),
    template="change.md",
)

# Diagram (DG) - Visual representations (binary)
_DIAGRAM_TYPE = TypeDefinition(
    prefix="DG",
    name="diagram",
    description="Visual representations of system aspects",
    category="binary",
    subtypes=(
        "architecture",
        "sequence",
        "flowchart",
        "erd",
        "state",
        "class",
        "deployment",
    ),
    type_fields=(
        TypeField(
            name="diagram_type",
            field_type="string",
            description="Type of diagram",
            allowed_values=(
                "architecture",
                "sequence",
                "flowchart",
                "erd",
                "state",
                "class",
                "deployment",
            ),
        ),
        TypeField(
            name="format",
            field_type="string",
            description="File format",
            allowed_values=("svg", "png", "pdf"),
        ),
        TypeField(
            name="source_file",
            field_type="string",
            description="Path to source file if generated",
        ),
        TypeField(
            name="dimensions",
            field_type="string",
            description="Width x height in pixels",
        ),
    ),
    formats=("svg", "png", "pdf"),
)

# Image (IM) - Visual references and documentation (binary)
_IMAGE_TYPE = TypeDefinition(
    prefix="IM",
    name="image",
    description="Visual references and documentation",
    category="binary",
    subtypes=("screenshot", "photo", "illustration", "reference"),
    type_fields=(
        TypeField(
            name="image_type",
            field_type="string",
            description="Type of image",
            allowed_values=("screenshot", "photo", "illustration", "reference"),
        ),
        TypeField(
            name="format",
            field_type="string",
            description="File format",
            allowed_values=("png", "jpg", "webp", "gif", "svg"),
        ),
        TypeField(
            name="dimensions",
            field_type="string",
            description="Width x height in pixels",
        ),
        TypeField(
            name="alt_text",
            field_type="string",
            description="Alternative text for accessibility",
            required=True,
        ),
        TypeField(
            name="source_url",
            field_type="string",
            description="URL to original if external reference",
        ),
        TypeField(
            name="capture_date",
            field_type="date",
            description="When screenshot/photo was taken",
        ),
    ),
    formats=("png", "jpg", "webp", "gif", "svg"),
)

# Video (VD) - Motion-based documentation (binary)
_VIDEO_TYPE = TypeDefinition(
    prefix="VD",
    name="video",
    description="Motion-based documentation",
    category="binary",
    subtypes=("screencast", "demo", "walkthrough", "tutorial"),
    type_fields=(
        TypeField(
            name="video_type",
            field_type="string",
            description="Type of video",
            allowed_values=("screencast", "demo", "walkthrough", "tutorial"),
        ),
        TypeField(
            name="format",
            field_type="string",
            description="File format",
            allowed_values=("mp4", "webm", "gif"),
        ),
        TypeField(
            name="duration",
            field_type="integer",
            description="Duration in seconds",
        ),
        TypeField(
            name="dimensions",
            field_type="string",
            description="Width x height in pixels",
        ),
        TypeField(
            name="transcript",
            field_type="string",
            description="Path to transcript file",
        ),
        TypeField(
            name="source_url",
            field_type="string",
            description="URL if hosted externally",
        ),
        TypeField(
            name="chapters",
            field_type="array",
            description="Chapter markers with timestamps",
        ),
    ),
    formats=("mp4", "webm", "gif"),
)

# Mockup (MK) - Visual design representations (binary)
_MOCKUP_TYPE = TypeDefinition(
    prefix="MK",
    name="mockup",
    description="Visual design representations",
    category="binary",
    subtypes=("wireframe", "mockup", "prototype", "comp"),
    type_fields=(
        TypeField(
            name="mockup_type",
            field_type="string",
            description="Type of mockup",
            allowed_values=("wireframe", "mockup", "prototype", "comp"),
        ),
        TypeField(
            name="format",
            field_type="string",
            description="File format",
            allowed_values=("png", "svg", "pdf", "figma", "sketch"),
        ),
        TypeField(
            name="dimensions",
            field_type="string",
            description="Width x height in pixels",
        ),
        TypeField(
            name="tool",
            field_type="string",
            description="Design tool used",
        ),
        TypeField(
            name="interactive_url",
            field_type="string",
            description="URL to interactive prototype",
        ),
    ),
    formats=("png", "svg", "pdf", "figma", "sketch"),
)

# =============================================================================
# Exports
# =============================================================================

BASE_TYPES: tuple[TypeDefinition, ...] = (
    _REVIEW_TYPE,
    _DECISION_TYPE,
    _ANALYSIS_TYPE,
    _REPORT_TYPE,
    _EXAMPLE_TYPE,
    _CHANGE_TYPE,
    _DIAGRAM_TYPE,
    _IMAGE_TYPE,
    _VIDEO_TYPE,
    _MOCKUP_TYPE,
)
"""All 10 base artifact types defined by the artifact system."""

RESERVED_PREFIXES: frozenset[str] = frozenset(t.prefix for t in BASE_TYPES)
"""Prefixes reserved for base types that cannot be used for custom types."""
