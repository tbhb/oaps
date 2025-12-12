"""Specification configuration models.

This module provides Pydantic models for specification settings including
ID prefixes, numbering format, and allowed status values.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class RequirementPrefixConfiguration(BaseModel):
    """Requirement type to prefix mapping."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    functional: str = Field(
        default="FR", description="Prefix for functional requirements."
    )
    quality: str = Field(default="QR", description="Prefix for quality requirements.")
    security: str = Field(default="SR", description="Prefix for security requirements.")
    accessibility: str = Field(
        default="AR", description="Prefix for accessibility requirements."
    )
    interface: str = Field(
        default="IR", description="Prefix for interface requirements."
    )
    documentation: str = Field(
        default="DR", description="Prefix for documentation requirements."
    )
    constraint: str = Field(
        default="CR", description="Prefix for constraint requirements."
    )


class TestPrefixConfiguration(BaseModel):
    """Test method to prefix mapping."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    unit: str = Field(default="UT", description="Prefix for unit tests.")
    integration: str = Field(default="NT", description="Prefix for integration tests.")
    e2e: str = Field(default="ET", description="Prefix for end-to-end tests.")
    performance: str = Field(default="PT", description="Prefix for performance tests.")
    conformance: str = Field(default="CT", description="Prefix for conformance tests.")
    accessibility: str = Field(
        default="AT", description="Prefix for accessibility tests."
    )
    smoke: str = Field(default="ST", description="Prefix for smoke tests.")
    manual: str = Field(default="MT", description="Prefix for manual tests.")
    fuzz: str = Field(default="FZ", description="Prefix for fuzz tests.")
    property: str = Field(default="HT", description="Prefix for property-based tests.")


class ArtifactPrefixConfiguration(BaseModel):
    """Artifact type to prefix mapping."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    review: str = Field(default="RV", description="Prefix for review artifacts.")
    change: str = Field(default="CH", description="Prefix for change artifacts.")
    analysis: str = Field(default="AN", description="Prefix for analysis artifacts.")
    decision: str = Field(default="DC", description="Prefix for decision records.")
    diagram: str = Field(default="DG", description="Prefix for diagram artifacts.")
    example: str = Field(default="EX", description="Prefix for example artifacts.")
    mockup: str = Field(default="MK", description="Prefix for mockup artifacts.")
    image: str = Field(default="IM", description="Prefix for image artifacts.")
    video: str = Field(default="VD", description="Prefix for video artifacts.")


class SpecPrefixesConfiguration(BaseModel):
    """Container for all prefix mappings."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    requirements: RequirementPrefixConfiguration = Field(
        default_factory=RequirementPrefixConfiguration,
        description="Requirement type to prefix mapping.",
    )
    tests: TestPrefixConfiguration = Field(
        default_factory=TestPrefixConfiguration,
        description="Test method to prefix mapping.",
    )
    artifacts: ArtifactPrefixConfiguration = Field(
        default_factory=ArtifactPrefixConfiguration,
        description="Artifact type to prefix mapping.",
    )


class SpecNumberingConfiguration(BaseModel):
    """ID numbering configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    digits: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Number of digits for identifiers (zero-padded).",
    )
    sub_separator: str = Field(
        default=".",
        pattern=r"^[.\-_]$",
        description="Separator for sub-requirements.",
    )


class SpecStatusesConfiguration(BaseModel):
    """Allowed status values per entity type."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    spec: list[str] = Field(
        default_factory=lambda: [
            "draft",
            "review",
            "approved",
            "implementing",
            "implemented",
            "verified",
            "deprecated",
            "superseded",
        ],
        description="Allowed status values for specifications.",
    )
    requirement: list[str] = Field(
        default_factory=lambda: [
            "proposed",
            "approved",
            "implementing",
            "implemented",
            "verified",
            "deferred",
            "rejected",
            "deprecated",
        ],
        description="Allowed status values for requirements.",
    )
    test: list[str] = Field(
        default_factory=lambda: [
            "pending",
            "implemented",
            "passing",
            "failing",
            "skipped",
            "flaky",
            "disabled",
        ],
        description="Allowed status values for tests.",
    )
    artifact: list[str] = Field(
        default_factory=lambda: ["draft", "complete", "superseded", "retracted"],
        description="Allowed status values for artifacts.",
    )


class SpecHooksValidationConfiguration(BaseModel):
    """Configuration for spec validation hooks.

    Controls which validations are performed during hook execution.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    precommit: bool = Field(
        default=True, description="Enable pre-commit validation of spec structure."
    )
    requirement_ids: bool = Field(
        default=True, description="Validate requirement ID format and uniqueness."
    )
    crossrefs: bool = Field(
        default=True, description="Validate cross-references between specs."
    )
    crossref_severity: str = Field(
        default="warning",
        pattern=r"^(error|warning|info)$",
        description="Severity level for cross-reference validation issues.",
    )


class SpecHooksSyncConfiguration(BaseModel):
    """Configuration for spec synchronization hooks.

    Controls automatic synchronization of spec metadata and indexes.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    test_results: bool = Field(
        default=True, description="Sync test results from pytest output."
    )
    coverage: bool = Field(
        default=True, description="Sync coverage data from coverage runs."
    )
    root_index: bool = Field(
        default=True, description="Sync root index.json after spec changes."
    )
    artifact_index: bool = Field(
        default=True, description="Sync artifacts.json after artifact changes."
    )


class SpecHooksHistoryConfiguration(BaseModel):
    """Configuration for spec history hooks.

    Controls automatic history recording for spec modifications.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    auto_record: bool = Field(
        default=True, description="Automatically record changes to history.jsonl."
    )
    detect_actor: bool = Field(
        default=True, description="Attempt to detect actor from environment."
    )
    default_actor: str = Field(
        default="user", description="Default actor when detection fails."
    )


class SpecHooksNotificationsConfiguration(BaseModel):
    """Configuration for spec notification hooks.

    Controls notifications for spec status changes and review requests.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    status_changes: bool = Field(
        default=True, description="Notify on spec status changes."
    )
    review_requests: bool = Field(
        default=True, description="Notify when spec is ready for review."
    )
    min_status_for_notification: str = Field(
        default="review",
        description="Minimum status level to trigger notifications.",
    )


class SpecHooksConfiguration(BaseModel):
    """Configuration for spec system hooks.

    Container for all spec hook configuration sections.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    validation: SpecHooksValidationConfiguration = Field(
        default_factory=SpecHooksValidationConfiguration,
        description="Validation hook settings.",
    )
    sync: SpecHooksSyncConfiguration = Field(
        default_factory=SpecHooksSyncConfiguration,
        description="Synchronization hook settings.",
    )
    history: SpecHooksHistoryConfiguration = Field(
        default_factory=SpecHooksHistoryConfiguration,
        description="History tracking hook settings.",
    )
    notifications: SpecHooksNotificationsConfiguration = Field(
        default_factory=SpecHooksNotificationsConfiguration,
        description="Notification hook settings.",
    )


class SpecConfiguration(BaseModel):
    """OAPS specification configuration.

    Controls ID prefixes, numbering format, and allowed status values
    for specs, requirements, tests, and artifacts.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    prefixes: SpecPrefixesConfiguration = Field(
        default_factory=SpecPrefixesConfiguration,
        description="Prefix mappings for IDs.",
    )
    numbering: SpecNumberingConfiguration = Field(
        default_factory=SpecNumberingConfiguration,
        description="ID numbering configuration.",
    )
    statuses: SpecStatusesConfiguration = Field(
        default_factory=SpecStatusesConfiguration,
        description="Allowed status values per entity type.",
    )
    hooks: SpecHooksConfiguration = Field(
        default_factory=SpecHooksConfiguration,
        description="Hook configuration for spec system.",
    )
