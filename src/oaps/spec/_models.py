"""Data models for the OAPS specification system.

This module defines all enums and dataclasses for specifications, requirements,
tests, and their supporting structures. All models are frozen dataclasses with
slots for immutability and memory efficiency.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

# =============================================================================
# Status Enums
# =============================================================================


class SpecStatus(StrEnum):
    """Specification lifecycle status values.

    Tracks the progression of a specification from initial draft through
    implementation, verification, and eventual deprecation.
    """

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class RequirementStatus(StrEnum):
    """Requirement lifecycle status values.

    Tracks the progression of a requirement from proposal through
    implementation and verification.
    """

    PROPOSED = "proposed"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class TestStatus(StrEnum):
    """Test execution status values.

    Tracks the current state of a test from pending implementation
    through execution results.
    """

    PENDING = "pending"
    IMPLEMENTED = "implemented"
    PASSING = "passing"
    FAILING = "failing"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    DISABLED = "disabled"


# =============================================================================
# Type Enums
# =============================================================================


class SpecType(StrEnum):
    """Specification architectural type values.

    Categorizes specifications by their role in the system architecture.
    """

    FOUNDATION = "foundation"
    SUBSYSTEM = "subsystem"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    INTEGRATION = "integration"
    DEPRECATED = "deprecated"


class RequirementType(StrEnum):
    """Requirement categorization types.

    Classifies requirements by their nature and purpose.
    """

    FUNCTIONAL = "functional"
    QUALITY = "quality"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    INTERFACE = "interface"
    DOCUMENTATION = "documentation"
    CONSTRAINT = "constraint"


class TestMethod(StrEnum):
    """Test methodology types.

    Categorizes tests by their execution approach and scope.
    """

    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    CONFORMANCE = "conformance"
    ACCESSIBILITY = "accessibility"
    SMOKE = "smoke"
    MANUAL = "manual"
    FUZZ = "fuzz"
    PROPERTY = "property"


class TestResult(StrEnum):
    """Test execution result values.

    Represents the outcome of a single test execution.
    """

    PASS = "pass"  # noqa: S105 - enum value, not password
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"


class DocumentType(StrEnum):
    """Document classification types.

    Categorizes documents by their role within a specification.
    """

    PRIMARY = "primary"
    SUPPLEMENTARY = "supplementary"
    APPENDIX = "appendix"


class ExternalRefType(StrEnum):
    """External reference classification types.

    Distinguishes between normative (binding) and informative references.
    """

    NORMATIVE = "normative"
    INFORMATIVE = "informative"


# =============================================================================
# Value Objects
# =============================================================================


@dataclass(frozen=True, slots=True)
class Document:
    """Document reference within a specification.

    Attributes:
        file: Relative path to the document file.
        title: Human-readable document title.
        doc_type: Classification of the document's role.
    """

    file: str
    title: str
    doc_type: DocumentType


@dataclass(frozen=True, slots=True)
class ExternalReference:
    """External reference to standards, RFCs, or other resources.

    Attributes:
        title: Human-readable reference title.
        url: URL to the external resource.
        ref_type: Whether the reference is normative or informative.
    """

    title: str
    url: str
    ref_type: ExternalRefType


@dataclass(frozen=True, slots=True)
class Relationships:
    """Spec relationship graph edges.

    Contains both user-specified outgoing relationships and computed
    inverse relationships populated by the index loader.

    Attributes:
        depends_on: IDs of specs this spec depends on.
        extends: ID of spec this spec extends.
        supersedes: ID of spec this spec supersedes.
        integrates: IDs of specs this spec integrates with.
        dependents: Computed inverse of depends_on.
        extended_by: Computed inverse of extends.
        superseded_by: Computed inverse of supersedes.
        integrated_by: Computed inverse of integrates.
    """

    # Outgoing relationships (user-specified)
    depends_on: tuple[str, ...] = ()
    extends: str | None = None
    supersedes: str | None = None
    integrates: tuple[str, ...] = ()
    # Computed inverse relationships
    dependents: tuple[str, ...] = ()
    extended_by: tuple[str, ...] = ()
    superseded_by: str | None = None
    integrated_by: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Counts:
    """Computed summary counts for a specification.

    Attributes:
        requirements: Total number of requirements.
        tests: Total number of tests.
        artifacts: Total number of artifacts.
    """

    requirements: int = 0
    tests: int = 0
    artifacts: int = 0


# =============================================================================
# Spec Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class SpecSummary:
    """Spec summary entry in the root index.

    Lightweight representation of a specification for listing purposes.

    Attributes:
        id: Unique specification identifier.
        slug: URL-friendly specification name.
        title: Human-readable specification title.
        spec_type: Architectural type of the specification.
        status: Current lifecycle status.
        created: Creation timestamp.
        updated: Last modification timestamp.
        depends_on: IDs of specs this spec depends on.
        tags: Freeform tags for filtering.
    """

    # Required
    id: str
    slug: str
    title: str
    spec_type: SpecType
    status: SpecStatus
    created: datetime
    updated: datetime
    # Optional
    depends_on: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpecMetadata:
    """Full specification metadata from per-spec index.json.

    Complete metadata for a specification including all relationships,
    documents, and external references.

    Attributes:
        id: Unique specification identifier.
        slug: URL-friendly specification name.
        title: Human-readable specification title.
        spec_type: Architectural type of the specification.
        status: Current lifecycle status.
        created: Creation timestamp.
        updated: Last modification timestamp.
        version: Specification version string.
        authors: List of author identifiers.
        reviewers: List of reviewer identifiers.
        relationships: Relationship graph edges.
        tags: Freeform tags for filtering.
        summary: Brief description for listings.
        documents: Document references within the specification.
        external_refs: External references to standards and resources.
        counts: Computed summary counts.
    """

    # Required
    id: str
    slug: str
    title: str
    spec_type: SpecType
    status: SpecStatus
    created: datetime
    updated: datetime
    # Optional
    version: str | None = None
    authors: tuple[str, ...] = ()
    reviewers: tuple[str, ...] = ()
    relationships: Relationships = field(default_factory=Relationships)
    tags: tuple[str, ...] = ()
    summary: str | None = None
    documents: tuple[Document, ...] = ()
    external_refs: tuple[ExternalReference, ...] = ()
    counts: Counts = field(default_factory=Counts)


# =============================================================================
# Core Entities
# =============================================================================


@dataclass(frozen=True, slots=True)
class Requirement:
    """Full requirement model with optional Planguage fields for quality requirements.

    Represents a single requirement with all metadata, traceability links,
    and optional Planguage fields for quantifiable quality requirements.

    Attributes:
        id: Unique requirement identifier.
        title: Human-readable requirement title.
        req_type: Categorization of the requirement.
        status: Current lifecycle status.
        created: Creation timestamp.
        updated: Last modification timestamp.
        author: Author identifier.
        description: Full requirement description.
        rationale: Explanation of why this requirement exists.
        acceptance_criteria: Criteria for verifying the requirement.
        verified_by: IDs of tests that verify this requirement.
        depends_on: IDs of requirements this depends on.
        tags: Freeform tags for filtering.
        source_section: Section of source document where requirement originated.
        parent: ID of parent requirement for sub-requirements.
        subtype: Further categorization within type.
        scale: Planguage scale definition for measurement.
        meter: Planguage meter definition for measurement method.
        baseline: Planguage baseline value (current state).
        goal: Planguage goal value (target to achieve).
        stretch: Planguage stretch value (aspirational target).
        fail: Planguage fail value (unacceptable threshold).
    """

    # Required
    id: str
    title: str
    req_type: RequirementType
    status: RequirementStatus
    created: datetime
    updated: datetime
    author: str
    description: str
    # Optional
    rationale: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    verified_by: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    source_section: str | None = None
    parent: str | None = None
    subtype: str | None = None
    # Planguage fields (for quality requirements)
    scale: str | None = None
    meter: str | None = None
    baseline: float | None = None
    goal: float | None = None
    stretch: float | None = None
    fail: float | None = None


@dataclass(frozen=True, slots=True)
class Test:
    """Full test model with method-specific optional fields.

    Represents a single test with all metadata, traceability links,
    and optional fields for specific test methods (performance, manual).

    Attributes:
        id: Unique test identifier.
        title: Human-readable test title.
        method: Test methodology type.
        status: Current execution status.
        created: Creation timestamp.
        updated: Last modification timestamp.
        author: Author identifier.
        tests_requirements: IDs of requirements this test verifies.
        description: Full test description.
        file: Path to test implementation file.
        function: Name of test function or method.
        last_run: Timestamp of last execution.
        last_result: Result of last execution.
        tags: Freeform tags for filtering.
        last_value: Last measured performance value.
        threshold: Performance threshold for pass/fail.
        perf_baseline: Performance baseline value.
        steps: Manual test steps.
        expected_result: Expected outcome for manual tests.
        actual_result: Actual outcome from manual test execution.
        tested_by: Identifier of manual test executor.
        tested_on: Timestamp of manual test execution.
    """

    # Required
    id: str
    title: str
    method: TestMethod
    status: TestStatus
    created: datetime
    updated: datetime
    author: str
    tests_requirements: tuple[str, ...]
    # Optional
    description: str | None = None
    file: str | None = None
    function: str | None = None
    last_run: datetime | None = None
    last_result: TestResult | None = None
    tags: tuple[str, ...] = ()
    # Performance test fields
    last_value: float | None = None
    threshold: float | None = None
    perf_baseline: float | None = None
    # Manual test fields
    steps: tuple[str, ...] = ()
    expected_result: str | None = None
    actual_result: str | None = None
    tested_by: str | None = None
    tested_on: datetime | None = None


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """History log entry from JSONL file.

    Represents a single event in the specification history log.

    Attributes:
        timestamp: When the event occurred.
        event: Type of event that occurred.
        actor: Identifier of who performed the action.
        command: Command that triggered the event.
        id: ID of the affected entity.
        target: Target of the action.
        from_value: Previous value (for status changes).
        to_value: New value (for status changes).
        result: Test result (for test runs).
        reason: Reason for the action.
    """

    # Required
    timestamp: datetime
    event: str
    actor: str
    # Optional
    command: str | None = None
    id: str | None = None
    target: str | None = None
    from_value: str | None = None
    to_value: str | None = None
    result: TestResult | None = None
    reason: str | None = None


# =============================================================================
# Container Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class RootIndex:
    """Root index.json structure.

    Top-level index file containing summary entries for all specifications.

    Attributes:
        version: Schema version number.
        updated: Last modification timestamp.
        specs: Summary entries for all specifications.
    """

    version: int
    updated: datetime
    specs: tuple[SpecSummary, ...]


@dataclass(frozen=True, slots=True)
class RequirementsContainer:
    """Requirements.json file structure.

    Container for all requirements within a specification.

    Attributes:
        version: Schema version number.
        spec_id: ID of the containing specification.
        updated: Last modification timestamp.
        requirements: All requirements in the specification.
    """

    version: int
    spec_id: str
    updated: datetime
    requirements: tuple[Requirement, ...]


@dataclass(frozen=True, slots=True)
class TestsContainer:
    """Tests.json file structure.

    Container for all tests within a specification.

    Attributes:
        version: Schema version number.
        spec_id: ID of the containing specification.
        updated: Last modification timestamp.
        tests: All tests in the specification.
    """

    version: int
    spec_id: str
    updated: datetime
    tests: tuple[Test, ...]


# =============================================================================
# Pytest Integration Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class PytestTest:
    """Single test result from pytest JSON report.

    Attributes:
        node_id: Pytest node ID (e.g., "tests/test_foo.py::test_bar").
        outcome: Test outcome ("passed", "failed", "skipped", "error").
        duration: Test duration in seconds.
        message: Optional error or skip message.
    """

    node_id: str
    outcome: str
    duration: float
    message: str | None = None


@dataclass(frozen=True, slots=True)
class PytestResults:
    """Parsed pytest JSON report.

    Attributes:
        tests: Tuple of individual test results.
        duration: Total test duration in seconds.
        exit_code: Pytest exit code.
    """

    tests: tuple[PytestTest, ...]
    duration: float
    exit_code: int


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Result of sync operation between pytest results and spec tests.

    Attributes:
        updated: Number of tests that were updated.
        orphaned: Number of pytest tests not matched to spec tests.
        skipped_no_file: Number of spec tests skipped due to missing file/function.
        errors: Tuple of error messages encountered during sync.
    """

    updated: int
    orphaned: int
    skipped_no_file: int
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RebuildResult:
    """Result of rebuilding an artifacts index.

    Attributes:
        scanned: Total number of files iterated.
        indexed: Number of artifacts successfully indexed.
        skipped: Number of files without valid metadata.
        errors: Tuple of error messages for files that raised exceptions.
    """

    scanned: int
    indexed: int
    skipped: int
    errors: tuple[str, ...]


# =============================================================================
# Artifact Models
# =============================================================================


class ArtifactType(StrEnum):
    """Artifact classification type.

    Categorizes artifacts by their role within a specification.
    """

    REVIEW = "review"
    CHANGE = "change"
    ANALYSIS = "analysis"
    DECISION = "decision"
    DIAGRAM = "diagram"
    EXAMPLE = "example"
    MOCKUP = "mockup"
    IMAGE = "image"
    VIDEO = "video"


class ArtifactStatus(StrEnum):
    """Artifact lifecycle status.

    Tracks the progression of an artifact through its lifecycle.
    """

    DRAFT = "draft"
    COMPLETE = "complete"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


# Import at module level for Artifact dataclass type annotations
from types import MappingProxyType  # noqa: E402
from typing import Any  # noqa: E402


def _empty_type_fields() -> MappingProxyType[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Create an empty MappingProxyType for type_fields default."""
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Artifact:
    """Specification artifact with support for text and binary formats.

    Represents a single artifact within a specification, such as reviews,
    decisions, diagrams, images, or videos.

    Attributes:
        id: Unique artifact identifier (e.g., "RV-0001").
        artifact_type: Classification of the artifact.
        title: Human-readable artifact title.
        status: Current lifecycle status.
        created: Creation timestamp.
        updated: Last modification timestamp.
        author: Author identifier.
        file_path: Relative path to artifact file within artifacts/ directory.
        description: Brief description of the artifact.
        subtype: Further categorization within type.
        references: IDs of related requirements or other artifacts.
        tags: Freeform tags for filtering.
        supersedes: ID of artifact this supersedes.
        superseded_by: ID of artifact that supersedes this.
        summary: Brief summary of artifact content.
        type_fields: Type-specific metadata fields.
        metadata_file_path: Path to sidecar metadata file for binary artifacts.
    """

    # Required
    id: str
    artifact_type: ArtifactType
    title: str
    status: ArtifactStatus
    created: datetime
    updated: datetime
    author: str
    file_path: str
    # Optional
    description: str | None = None
    subtype: str | None = None
    references: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    supersedes: str | None = None
    superseded_by: str | None = None
    summary: str | None = None
    type_fields: MappingProxyType[str, Any] = field(  # pyright: ignore[reportExplicitAny]
        default_factory=_empty_type_fields
    )
    metadata_file_path: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactsContainer:
    """Container for artifacts.json file structure.

    Top-level structure for the artifacts index file within a specification.

    Attributes:
        version: Schema version number.
        spec_id: ID of the containing specification.
        updated: Last modification timestamp.
        artifacts: All artifacts in the specification.
    """

    version: int
    spec_id: str
    updated: datetime
    artifacts: tuple[Artifact, ...]


# =============================================================================
# Relationship Types
# =============================================================================


class RelationshipType(StrEnum):
    """Specification relationship type values.

    Categorizes the types of relationships between specifications.
    """

    DEPENDS_ON = "depends_on"
    EXTENDS = "extends"
    SUPERSEDES = "supersedes"
    INTEGRATES = "integrates"


# =============================================================================
# Progress Report Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class TypeProgress:
    """Implementation progress by requirement type.

    Attributes:
        req_type: The requirement type.
        total: Total number of requirements of this type.
        implemented: Number of implemented requirements.
        verified: Number of verified requirements.
        percentage: Implementation percentage (0-100).
    """

    req_type: RequirementType
    total: int
    implemented: int
    verified: int
    percentage: float


@dataclass(frozen=True, slots=True)
class ProgressReport:
    """Implementation progress report for a specification.

    Attributes:
        spec_id: The specification ID.
        total_requirements: Total number of requirements.
        implemented_requirements: Number of implemented requirements.
        verified_requirements: Number of verified requirements.
        overall_percentage: Overall implementation percentage (0-100).
        by_type: Progress breakdown by requirement type.
    """

    spec_id: str
    total_requirements: int
    implemented_requirements: int
    verified_requirements: int
    overall_percentage: float
    by_type: tuple[TypeProgress, ...]


# =============================================================================
# Coverage Report Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class MethodCoverage:
    """Test coverage by test method.

    Attributes:
        method: The test method type.
        total_tests: Total number of tests using this method.
        passing_tests: Number of passing tests.
        requirements_covered: Number of unique requirements covered by passing tests.
    """

    method: TestMethod
    total_tests: int
    passing_tests: int
    requirements_covered: int


@dataclass(frozen=True, slots=True)
class TypeCoverage:
    """Test coverage by requirement type.

    Attributes:
        req_type: The requirement type.
        total_requirements: Total number of requirements of this type.
        covered_requirements: Number of requirements with at least one passing test.
        coverage_percentage: Coverage percentage (0-100).
    """

    req_type: RequirementType
    total_requirements: int
    covered_requirements: int
    coverage_percentage: float


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Test coverage report for a specification.

    Attributes:
        spec_id: The specification ID.
        total_requirements: Total number of requirements.
        covered_requirements: Number of requirements with at least one passing test.
        overall_coverage: Overall coverage percentage (0-100).
        by_method: Coverage breakdown by test method.
        by_type: Coverage breakdown by requirement type.
        requirement_to_tests: Mapping of requirement IDs to their passing test IDs.
    """

    spec_id: str
    total_requirements: int
    covered_requirements: int
    overall_coverage: float
    by_method: tuple[MethodCoverage, ...]
    by_type: tuple[TypeCoverage, ...]
    requirement_to_tests: MappingProxyType[str, tuple[str, ...]]


# =============================================================================
# Orphan Report Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class OrphanReport:
    """Report of orphaned tests and artifacts.

    Attributes:
        spec_id: The specification ID.
        orphaned_tests: Tests that reference no valid requirements.
        orphaned_artifacts: Artifact IDs that reference no valid entities.
        tests_missing_file: Tests that have no file and function defined.
    """

    spec_id: str
    orphaned_tests: tuple[Test, ...]
    orphaned_artifacts: tuple[str, ...]
    tests_missing_file: tuple[Test, ...]


# =============================================================================
# Dependency Graph Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class DependencyNode:
    """Node in a dependency graph.

    Attributes:
        spec_id: The specification ID.
        title: The specification title.
        status: Current lifecycle status.
        depth: Depth in the dependency tree from the root.
    """

    spec_id: str
    title: str
    status: SpecStatus
    depth: int


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    """Dependency graph for specifications.

    Attributes:
        nodes: All nodes in the graph.
        edges: All edges as (from_spec_id, to_spec_id) tuples.
        roots: Spec IDs with no incoming dependencies.
        leaves: Spec IDs with no outgoing dependencies.
        topological_order: Specs in topological order (empty if cycles exist).
        has_cycles: Whether the graph contains cycles.
        cycle_path: Path of the first detected cycle (empty if no cycles).
    """

    nodes: tuple[DependencyNode, ...]
    edges: tuple[tuple[str, str], ...]
    roots: tuple[str, ...]
    leaves: tuple[str, ...]
    topological_order: tuple[str, ...]
    has_cycles: bool
    cycle_path: tuple[str, ...]


# =============================================================================
# Relationship Graph Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class SpecNode:
    """Node representing a specification in a relationship graph.

    Attributes:
        spec_id: The specification ID.
        title: The specification title.
        spec_type: Architectural type of the specification.
        status: Current lifecycle status.
    """

    spec_id: str
    title: str
    spec_type: SpecType
    status: SpecStatus


@dataclass(frozen=True, slots=True)
class RelationshipEdge:
    """Edge representing a relationship between specifications.

    Attributes:
        from_spec_id: The source specification ID.
        to_spec_id: The target specification ID.
        relationship_type: The type of relationship.
    """

    from_spec_id: str
    to_spec_id: str
    relationship_type: RelationshipType


@dataclass(frozen=True, slots=True)
class RelationshipGraph:
    """Complete relationship graph for specifications.

    Attributes:
        nodes: All nodes in the graph.
        edges: All edges with their relationship types.
        node_index: Mapping of spec IDs to their SpecNode objects.
    """

    nodes: tuple[SpecNode, ...]
    edges: tuple[RelationshipEdge, ...]
    node_index: MappingProxyType[str, SpecNode]
