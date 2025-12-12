from collections.abc import Callable
from datetime import datetime
from types import MappingProxyType

from oaps.spec._models import (
    Artifact,
    ArtifactsContainer,
    ArtifactStatus,
    ArtifactType,
    Counts,
    CoverageReport,
    DependencyGraph,
    DependencyNode,
    Document,
    DocumentType,
    ExternalReference,
    ExternalRefType,
    HistoryEntry,
    MethodCoverage,
    OrphanReport,
    ProgressReport,
    PytestResults,
    PytestTest,
    RebuildResult,
    RelationshipEdge,
    RelationshipGraph,
    Relationships,
    RelationshipType,
    Requirement,
    RequirementsContainer,
    RequirementStatus,
    RequirementType,
    RootIndex,
    SpecMetadata,
    SpecNode,
    SpecStatus,
    SpecSummary,
    SpecType,
    SyncResult,
    Test as SpecTest,
    TestMethod as SpecTestMethod,
    TestResult as SpecTestResult,
    TestsContainer as SpecTestsContainer,
    TestStatus as SpecTestStatus,
    TypeCoverage,
    TypeProgress,
)

# =============================================================================
# Status Enums
# =============================================================================


class TestSpecStatus:
    def test_values(self) -> None:
        assert SpecStatus.DRAFT == "draft"
        assert SpecStatus.REVIEW == "review"
        assert SpecStatus.APPROVED == "approved"
        assert SpecStatus.IMPLEMENTING == "implementing"
        assert SpecStatus.IMPLEMENTED == "implemented"
        assert SpecStatus.VERIFIED == "verified"
        assert SpecStatus.DEPRECATED == "deprecated"
        assert SpecStatus.SUPERSEDED == "superseded"

    def test_member_count(self) -> None:
        assert len(SpecStatus) == 8

    def test_order(self) -> None:
        lifecycle = [
            SpecStatus.DRAFT,
            SpecStatus.REVIEW,
            SpecStatus.APPROVED,
            SpecStatus.IMPLEMENTING,
            SpecStatus.IMPLEMENTED,
            SpecStatus.VERIFIED,
            SpecStatus.DEPRECATED,
            SpecStatus.SUPERSEDED,
        ]
        assert list(SpecStatus) == lifecycle


class TestRequirementStatus:
    def test_values(self) -> None:
        assert RequirementStatus.PROPOSED == "proposed"
        assert RequirementStatus.APPROVED == "approved"
        assert RequirementStatus.IMPLEMENTING == "implementing"
        assert RequirementStatus.IMPLEMENTED == "implemented"
        assert RequirementStatus.VERIFIED == "verified"
        assert RequirementStatus.DEFERRED == "deferred"
        assert RequirementStatus.REJECTED == "rejected"
        assert RequirementStatus.DEPRECATED == "deprecated"

    def test_member_count(self) -> None:
        assert len(RequirementStatus) == 8

    def test_order(self) -> None:
        lifecycle = [
            RequirementStatus.PROPOSED,
            RequirementStatus.APPROVED,
            RequirementStatus.IMPLEMENTING,
            RequirementStatus.IMPLEMENTED,
            RequirementStatus.VERIFIED,
            RequirementStatus.DEFERRED,
            RequirementStatus.REJECTED,
            RequirementStatus.DEPRECATED,
        ]
        assert list(RequirementStatus) == lifecycle


class TestSpecTestStatus:
    def test_values(self) -> None:
        assert SpecTestStatus.PENDING == "pending"
        assert SpecTestStatus.IMPLEMENTED == "implemented"
        assert SpecTestStatus.PASSING == "passing"
        assert SpecTestStatus.FAILING == "failing"
        assert SpecTestStatus.SKIPPED == "skipped"
        assert SpecTestStatus.FLAKY == "flaky"
        assert SpecTestStatus.DISABLED == "disabled"

    def test_member_count(self) -> None:
        assert len(SpecTestStatus) == 7

    def test_order(self) -> None:
        lifecycle = [
            SpecTestStatus.PENDING,
            SpecTestStatus.IMPLEMENTED,
            SpecTestStatus.PASSING,
            SpecTestStatus.FAILING,
            SpecTestStatus.SKIPPED,
            SpecTestStatus.FLAKY,
            SpecTestStatus.DISABLED,
        ]
        assert list(SpecTestStatus) == lifecycle


# =============================================================================
# Type Enums
# =============================================================================


class TestSpecType:
    def test_values(self) -> None:
        assert SpecType.FOUNDATION == "foundation"
        assert SpecType.SUBSYSTEM == "subsystem"
        assert SpecType.FEATURE == "feature"
        assert SpecType.ENHANCEMENT == "enhancement"
        assert SpecType.INTEGRATION == "integration"
        assert SpecType.DEPRECATED == "deprecated"

    def test_member_count(self) -> None:
        assert len(SpecType) == 6


class TestRequirementType:
    def test_values(self) -> None:
        assert RequirementType.FUNCTIONAL == "functional"
        assert RequirementType.QUALITY == "quality"
        assert RequirementType.SECURITY == "security"
        assert RequirementType.ACCESSIBILITY == "accessibility"
        assert RequirementType.INTERFACE == "interface"
        assert RequirementType.DOCUMENTATION == "documentation"
        assert RequirementType.CONSTRAINT == "constraint"

    def test_member_count(self) -> None:
        assert len(RequirementType) == 7


class TestSpecTestMethod:
    def test_values(self) -> None:
        assert SpecTestMethod.UNIT == "unit"
        assert SpecTestMethod.INTEGRATION == "integration"
        assert SpecTestMethod.E2E == "e2e"
        assert SpecTestMethod.PERFORMANCE == "performance"
        assert SpecTestMethod.CONFORMANCE == "conformance"
        assert SpecTestMethod.ACCESSIBILITY == "accessibility"
        assert SpecTestMethod.SMOKE == "smoke"
        assert SpecTestMethod.MANUAL == "manual"
        assert SpecTestMethod.FUZZ == "fuzz"
        assert SpecTestMethod.PROPERTY == "property"

    def test_member_count(self) -> None:
        assert len(SpecTestMethod) == 10


class TestSpecTestResult:
    def test_values(self) -> None:
        assert SpecTestResult.PASS == "pass"  # noqa: S105
        assert SpecTestResult.FAIL == "fail"
        assert SpecTestResult.SKIP == "skip"
        assert SpecTestResult.ERROR == "error"

    def test_member_count(self) -> None:
        assert len(SpecTestResult) == 4


class TestDocumentType:
    def test_values(self) -> None:
        assert DocumentType.PRIMARY == "primary"
        assert DocumentType.SUPPLEMENTARY == "supplementary"
        assert DocumentType.APPENDIX == "appendix"

    def test_member_count(self) -> None:
        assert len(DocumentType) == 3


class TestExternalRefType:
    def test_values(self) -> None:
        assert ExternalRefType.NORMATIVE == "normative"
        assert ExternalRefType.INFORMATIVE == "informative"

    def test_member_count(self) -> None:
        assert len(ExternalRefType) == 2


class TestArtifactType:
    def test_values(self) -> None:
        assert ArtifactType.REVIEW == "review"
        assert ArtifactType.CHANGE == "change"
        assert ArtifactType.ANALYSIS == "analysis"
        assert ArtifactType.DECISION == "decision"
        assert ArtifactType.DIAGRAM == "diagram"
        assert ArtifactType.EXAMPLE == "example"
        assert ArtifactType.MOCKUP == "mockup"
        assert ArtifactType.IMAGE == "image"
        assert ArtifactType.VIDEO == "video"

    def test_member_count(self) -> None:
        assert len(ArtifactType) == 9


class TestArtifactStatus:
    def test_values(self) -> None:
        assert ArtifactStatus.DRAFT == "draft"
        assert ArtifactStatus.COMPLETE == "complete"
        assert ArtifactStatus.SUPERSEDED == "superseded"
        assert ArtifactStatus.RETRACTED == "retracted"

    def test_member_count(self) -> None:
        assert len(ArtifactStatus) == 4


class TestRelationshipType:
    def test_values(self) -> None:
        assert RelationshipType.DEPENDS_ON == "depends_on"
        assert RelationshipType.EXTENDS == "extends"
        assert RelationshipType.SUPERSEDES == "supersedes"
        assert RelationshipType.INTEGRATES == "integrates"

    def test_member_count(self) -> None:
        assert len(RelationshipType) == 4


# =============================================================================
# Value Objects
# =============================================================================


class TestDocument:
    def test_creates_with_required_fields(self) -> None:
        doc = Document(
            file="spec.md",
            title="Specification",
            doc_type=DocumentType.PRIMARY,
        )
        assert doc.file == "spec.md"
        assert doc.title == "Specification"
        assert doc.doc_type == DocumentType.PRIMARY

    def test_is_frozen(self) -> None:
        doc = Document(
            file="spec.md",
            title="Specification",
            doc_type=DocumentType.PRIMARY,
        )
        raised = False
        try:
            doc.file = "other.md"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(Document, "__slots__")


class TestExternalReference:
    def test_creates_with_required_fields(self) -> None:
        ref = ExternalReference(
            title="RFC 2119",
            url="https://www.rfc-editor.org/rfc/rfc2119",
            ref_type=ExternalRefType.NORMATIVE,
        )
        assert ref.title == "RFC 2119"
        assert ref.url == "https://www.rfc-editor.org/rfc/rfc2119"
        assert ref.ref_type == ExternalRefType.NORMATIVE

    def test_is_frozen(self) -> None:
        ref = ExternalReference(
            title="RFC 2119",
            url="https://www.rfc-editor.org/rfc/rfc2119",
            ref_type=ExternalRefType.NORMATIVE,
        )
        raised = False
        try:
            ref.title = "Other"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(ExternalReference, "__slots__")


class TestRelationships:
    def test_creates_with_required_fields(self) -> None:
        rel = Relationships()
        assert rel.depends_on == ()
        assert rel.extends is None
        assert rel.supersedes is None
        assert rel.integrates == ()
        assert rel.dependents == ()
        assert rel.extended_by == ()
        assert rel.superseded_by is None
        assert rel.integrated_by == ()

    def test_optional_field_defaults(self) -> None:
        rel = Relationships(
            depends_on=("SPEC-0001", "SPEC-0002"),
            extends="SPEC-0003",
            supersedes="SPEC-0004",
            integrates=("SPEC-0005",),
        )
        assert rel.depends_on == ("SPEC-0001", "SPEC-0002")
        assert rel.extends == "SPEC-0003"
        assert rel.supersedes == "SPEC-0004"
        assert rel.integrates == ("SPEC-0005",)

    def test_tuple_fields_preserve_values(self) -> None:
        rel = Relationships(
            depends_on=("A", "B", "C"),
            integrates=("X", "Y"),
            dependents=("D", "E"),
            extended_by=("F",),
            integrated_by=("G", "H", "I"),
        )
        assert rel.depends_on == ("A", "B", "C")
        assert rel.integrates == ("X", "Y")
        assert rel.dependents == ("D", "E")
        assert rel.extended_by == ("F",)
        assert rel.integrated_by == ("G", "H", "I")

    def test_is_frozen(self) -> None:
        rel = Relationships()
        raised = False
        try:
            rel.depends_on = ("SPEC-0001",)  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(Relationships, "__slots__")


class TestCounts:
    def test_creates_with_required_fields(self) -> None:
        counts = Counts()
        assert counts.requirements == 0
        assert counts.tests == 0
        assert counts.artifacts == 0

    def test_optional_field_defaults(self) -> None:
        counts = Counts(requirements=5, tests=10, artifacts=3)
        assert counts.requirements == 5
        assert counts.tests == 10
        assert counts.artifacts == 3

    def test_is_frozen(self) -> None:
        counts = Counts()
        raised = False
        try:
            counts.requirements = 5  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(Counts, "__slots__")


# =============================================================================
# Spec Models
# =============================================================================


class TestSpecSummary:
    def test_creates_with_required_fields_only(
        self, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary = make_spec_summary()
        assert summary.id == "SPEC-0001"
        assert summary.slug == "test-spec"
        assert summary.title == "Test Specification"
        assert summary.spec_type == SpecType.FEATURE
        assert summary.status == SpecStatus.DRAFT

    def test_optional_field_defaults(
        self, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary = make_spec_summary()
        assert summary.depends_on == ()
        assert summary.tags == ()

    def test_tuple_fields_preserve_values(
        self, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary = make_spec_summary(
            depends_on=("SPEC-0002", "SPEC-0003"),
            tags=("core", "api"),
        )
        assert summary.depends_on == ("SPEC-0002", "SPEC-0003")
        assert summary.tags == ("core", "api")

    def test_is_frozen(self, make_spec_summary: Callable[..., SpecSummary]) -> None:
        summary = make_spec_summary()
        raised = False
        try:
            summary.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SpecSummary, "__slots__")


class TestSpecMetadata:
    def test_creates_with_required_fields_only(
        self, make_spec_metadata: Callable[..., SpecMetadata]
    ) -> None:
        meta = make_spec_metadata()
        assert meta.id == "SPEC-0001"
        assert meta.slug == "test-spec"
        assert meta.title == "Test Specification"
        assert meta.spec_type == SpecType.FEATURE
        assert meta.status == SpecStatus.DRAFT

    def test_optional_field_defaults(
        self, make_spec_metadata: Callable[..., SpecMetadata]
    ) -> None:
        meta = make_spec_metadata()
        assert meta.version is None
        assert meta.authors == ()
        assert meta.reviewers == ()
        assert meta.relationships == Relationships()
        assert meta.tags == ()
        assert meta.summary is None
        assert meta.documents == ()
        assert meta.external_refs == ()
        assert meta.counts == Counts()

    def test_tuple_fields_preserve_values(
        self, make_spec_metadata: Callable[..., SpecMetadata]
    ) -> None:
        doc = Document(file="spec.md", title="Spec", doc_type=DocumentType.PRIMARY)
        ref = ExternalReference(
            title="RFC", url="http://example.com", ref_type=ExternalRefType.NORMATIVE
        )
        meta = make_spec_metadata(
            authors=("author1", "author2"),
            reviewers=("reviewer1",),
            tags=("tag1", "tag2", "tag3"),
            documents=(doc,),
            external_refs=(ref,),
        )
        assert meta.authors == ("author1", "author2")
        assert meta.reviewers == ("reviewer1",)
        assert meta.tags == ("tag1", "tag2", "tag3")
        assert meta.documents == (doc,)
        assert meta.external_refs == (ref,)

    def test_is_frozen(self, make_spec_metadata: Callable[..., SpecMetadata]) -> None:
        meta = make_spec_metadata()
        raised = False
        try:
            meta.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SpecMetadata, "__slots__")


# =============================================================================
# Core Entities
# =============================================================================


class TestRequirement:
    def test_creates_with_required_fields_only(
        self, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement()
        assert req.id == "REQ-0001"
        assert req.title == "Test Requirement"
        assert req.req_type == RequirementType.FUNCTIONAL
        assert req.status == RequirementStatus.PROPOSED
        assert req.author == "test-author"
        assert req.description == "Test requirement description"

    def test_optional_field_defaults(
        self, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement()
        assert req.rationale is None
        assert req.acceptance_criteria == ()
        assert req.verified_by == ()
        assert req.depends_on == ()
        assert req.tags == ()
        assert req.source_section is None
        assert req.parent is None
        assert req.subtype is None
        assert req.scale is None
        assert req.meter is None
        assert req.baseline is None
        assert req.goal is None
        assert req.stretch is None
        assert req.fail is None

    def test_tuple_fields_preserve_values(
        self, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement(
            acceptance_criteria=("criteria1", "criteria2"),
            verified_by=("TST-0001", "TST-0002"),
            depends_on=("REQ-0002",),
            tags=("security", "performance"),
        )
        assert req.acceptance_criteria == ("criteria1", "criteria2")
        assert req.verified_by == ("TST-0001", "TST-0002")
        assert req.depends_on == ("REQ-0002",)
        assert req.tags == ("security", "performance")

    def test_planguage_fields(
        self, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement(
            scale="response time in milliseconds",
            meter="95th percentile over 24 hours",
            baseline=500.0,
            goal=100.0,
            stretch=50.0,
            fail=1000.0,
        )
        assert req.scale == "response time in milliseconds"
        assert req.meter == "95th percentile over 24 hours"
        assert req.baseline == 500.0
        assert req.goal == 100.0
        assert req.stretch == 50.0
        assert req.fail == 1000.0

    def test_is_frozen(self, make_requirement: Callable[..., Requirement]) -> None:
        req = make_requirement()
        raised = False
        try:
            req.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(Requirement, "__slots__")


class TestSpecTest:
    def test_creates_with_required_fields_only(
        self, make_test: Callable[..., SpecTest]
    ) -> None:
        test = make_test()
        assert test.id == "TST-0001"
        assert test.title == "Test Case"
        assert test.method == SpecTestMethod.UNIT
        assert test.status == SpecTestStatus.PENDING
        assert test.author == "test-author"
        assert test.tests_requirements == ("REQ-0001",)

    def test_optional_field_defaults(self, make_test: Callable[..., SpecTest]) -> None:
        test = make_test()
        assert test.description is None
        assert test.file is None
        assert test.function is None
        assert test.last_run is None
        assert test.last_result is None
        assert test.tags == ()
        assert test.last_value is None
        assert test.threshold is None
        assert test.perf_baseline is None
        assert test.steps == ()
        assert test.expected_result is None
        assert test.actual_result is None
        assert test.tested_by is None
        assert test.tested_on is None

    def test_tuple_fields_preserve_values(
        self, make_test: Callable[..., SpecTest]
    ) -> None:
        test = make_test(
            tests_requirements=("REQ-0001", "REQ-0002", "REQ-0003"),
            tags=("unit", "fast"),
            steps=("Step 1", "Step 2", "Step 3"),
        )
        assert test.tests_requirements == ("REQ-0001", "REQ-0002", "REQ-0003")
        assert test.tags == ("unit", "fast")
        assert test.steps == ("Step 1", "Step 2", "Step 3")

    def test_performance_test_fields(self, make_test: Callable[..., SpecTest]) -> None:
        test = make_test(
            method=SpecTestMethod.PERFORMANCE,
            last_value=95.5,
            threshold=100.0,
            perf_baseline=120.0,
        )
        assert test.last_value == 95.5
        assert test.threshold == 100.0
        assert test.perf_baseline == 120.0

    def test_manual_test_fields(
        self, make_test: Callable[..., SpecTest], sample_datetime: datetime
    ) -> None:
        test = make_test(
            method=SpecTestMethod.MANUAL,
            steps=("Open app", "Click button", "Verify result"),
            expected_result="Button changes color",
            actual_result="Button changed color",
            tested_by="qa-engineer",
            tested_on=sample_datetime,
        )
        assert test.steps == ("Open app", "Click button", "Verify result")
        assert test.expected_result == "Button changes color"
        assert test.actual_result == "Button changed color"
        assert test.tested_by == "qa-engineer"
        assert test.tested_on == sample_datetime

    def test_is_frozen(self, make_test: Callable[..., SpecTest]) -> None:
        test = make_test()
        raised = False
        try:
            test.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SpecTest, "__slots__")


class TestHistoryEntry:
    def test_creates_with_required_fields_only(
        self, make_history_entry: Callable[..., HistoryEntry]
    ) -> None:
        entry = make_history_entry()
        assert entry.event == "spec_created"
        assert entry.actor == "test-actor"
        assert entry.timestamp is not None

    def test_optional_field_defaults(
        self, make_history_entry: Callable[..., HistoryEntry]
    ) -> None:
        entry = make_history_entry()
        assert entry.command is None
        assert entry.id is None
        assert entry.target is None
        assert entry.from_value is None
        assert entry.to_value is None
        assert entry.result is None
        assert entry.reason is None

    def test_is_frozen(self, make_history_entry: Callable[..., HistoryEntry]) -> None:
        entry = make_history_entry()
        raised = False
        try:
            entry.event = "modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(HistoryEntry, "__slots__")


# =============================================================================
# Artifact Models
# =============================================================================


class TestArtifact:
    def test_creates_with_required_fields_only(
        self, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact = make_artifact()
        assert artifact.id == "RV-0001"
        assert artifact.artifact_type == ArtifactType.REVIEW
        assert artifact.title == "Test Artifact"
        assert artifact.status == ArtifactStatus.DRAFT
        assert artifact.author == "test-author"
        assert artifact.file_path == "artifacts/RV-0001.md"

    def test_optional_field_defaults(
        self, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact = make_artifact()
        assert artifact.description is None
        assert artifact.subtype is None
        assert artifact.references == ()
        assert artifact.tags == ()
        assert artifact.supersedes is None
        assert artifact.superseded_by is None
        assert artifact.summary is None
        assert artifact.metadata_file_path is None

    def test_type_fields_default(self, make_artifact: Callable[..., Artifact]) -> None:
        artifact = make_artifact()
        assert artifact.type_fields == MappingProxyType({})
        assert isinstance(artifact.type_fields, MappingProxyType)

    def test_type_fields_with_values(
        self, make_artifact: Callable[..., Artifact]
    ) -> None:
        type_fields = MappingProxyType({"decision_outcome": "approved", "votes": 5})
        artifact = make_artifact(type_fields=type_fields)
        assert artifact.type_fields == MappingProxyType(
            {"decision_outcome": "approved", "votes": 5}
        )

    def test_tuple_fields_preserve_values(
        self, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact = make_artifact(
            references=("REQ-0001", "REQ-0002"),
            tags=("review", "architecture"),
        )
        assert artifact.references == ("REQ-0001", "REQ-0002")
        assert artifact.tags == ("review", "architecture")

    def test_is_frozen(self, make_artifact: Callable[..., Artifact]) -> None:
        artifact = make_artifact()
        raised = False
        try:
            artifact.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(Artifact, "__slots__")


# =============================================================================
# Container Models
# =============================================================================


class TestRootIndex:
    def test_creates_with_required_fields(
        self, sample_datetime: datetime, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary = make_spec_summary()
        index = RootIndex(version=1, updated=sample_datetime, specs=(summary,))
        assert index.version == 1
        assert index.updated == sample_datetime
        assert index.specs == (summary,)

    def test_items_tuple_preserved(
        self, sample_datetime: datetime, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary1 = make_spec_summary(id="SPEC-0001")
        summary2 = make_spec_summary(id="SPEC-0002")
        index = RootIndex(
            version=1, updated=sample_datetime, specs=(summary1, summary2)
        )
        assert len(index.specs) == 2
        assert index.specs[0].id == "SPEC-0001"
        assert index.specs[1].id == "SPEC-0002"

    def test_is_frozen(
        self, sample_datetime: datetime, make_spec_summary: Callable[..., SpecSummary]
    ) -> None:
        summary = make_spec_summary()
        index = RootIndex(version=1, updated=sample_datetime, specs=(summary,))
        raised = False
        try:
            index.version = 2  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(RootIndex, "__slots__")


class TestRequirementsContainer:
    def test_creates_with_required_fields(
        self, sample_datetime: datetime, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement()
        container = RequirementsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            requirements=(req,),
        )
        assert container.version == 1
        assert container.spec_id == "SPEC-0001"
        assert container.updated == sample_datetime
        assert container.requirements == (req,)

    def test_items_tuple_preserved(
        self, sample_datetime: datetime, make_requirement: Callable[..., Requirement]
    ) -> None:
        req1 = make_requirement(id="REQ-0001")
        req2 = make_requirement(id="REQ-0002")
        container = RequirementsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            requirements=(req1, req2),
        )
        assert len(container.requirements) == 2
        assert container.requirements[0].id == "REQ-0001"
        assert container.requirements[1].id == "REQ-0002"

    def test_is_frozen(
        self, sample_datetime: datetime, make_requirement: Callable[..., Requirement]
    ) -> None:
        req = make_requirement()
        container = RequirementsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            requirements=(req,),
        )
        raised = False
        try:
            container.version = 2  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(RequirementsContainer, "__slots__")


class TestSpecTestsContainer:
    def test_creates_with_required_fields(
        self, sample_datetime: datetime, make_test: Callable[..., SpecTest]
    ) -> None:
        test = make_test()
        container = SpecTestsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            tests=(test,),
        )
        assert container.version == 1
        assert container.spec_id == "SPEC-0001"
        assert container.updated == sample_datetime
        assert container.tests == (test,)

    def test_items_tuple_preserved(
        self, sample_datetime: datetime, make_test: Callable[..., SpecTest]
    ) -> None:
        test1 = make_test(id="TST-0001")
        test2 = make_test(id="TST-0002")
        container = SpecTestsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            tests=(test1, test2),
        )
        assert len(container.tests) == 2
        assert container.tests[0].id == "TST-0001"
        assert container.tests[1].id == "TST-0002"

    def test_is_frozen(
        self, sample_datetime: datetime, make_test: Callable[..., SpecTest]
    ) -> None:
        test = make_test()
        container = SpecTestsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            tests=(test,),
        )
        raised = False
        try:
            container.version = 2  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SpecTestsContainer, "__slots__")


class TestArtifactsContainer:
    def test_creates_with_required_fields(
        self, sample_datetime: datetime, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact = make_artifact()
        container = ArtifactsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            artifacts=(artifact,),
        )
        assert container.version == 1
        assert container.spec_id == "SPEC-0001"
        assert container.updated == sample_datetime
        assert container.artifacts == (artifact,)

    def test_items_tuple_preserved(
        self, sample_datetime: datetime, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact1 = make_artifact(id="RV-0001")
        artifact2 = make_artifact(id="RV-0002")
        container = ArtifactsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            artifacts=(artifact1, artifact2),
        )
        assert len(container.artifacts) == 2
        assert container.artifacts[0].id == "RV-0001"
        assert container.artifacts[1].id == "RV-0002"

    def test_is_frozen(
        self, sample_datetime: datetime, make_artifact: Callable[..., Artifact]
    ) -> None:
        artifact = make_artifact()
        container = ArtifactsContainer(
            version=1,
            spec_id="SPEC-0001",
            updated=sample_datetime,
            artifacts=(artifact,),
        )
        raised = False
        try:
            container.version = 2  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(ArtifactsContainer, "__slots__")


# =============================================================================
# Pytest Integration Models
# =============================================================================


class TestPytestTest:
    def test_creates_with_required_fields(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.123,
        )
        assert test.node_id == "tests/test_foo.py::test_bar"
        assert test.outcome == "passed"
        assert test.duration == 0.123

    def test_optional_defaults(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.123,
        )
        assert test.message is None

    def test_message_field(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="failed",
            duration=0.456,
            message="AssertionError: expected True",
        )
        assert test.message == "AssertionError: expected True"

    def test_is_frozen(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.123,
        )
        raised = False
        try:
            test.outcome = "failed"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(PytestTest, "__slots__")


class TestPytestResults:
    def test_creates_with_required_fields(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.123,
        )
        results = PytestResults(
            tests=(test,),
            duration=1.5,
            exit_code=0,
        )
        assert results.tests == (test,)
        assert results.duration == 1.5
        assert results.exit_code == 0

    def test_tuple_fields_preserve_values(self) -> None:
        test1 = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.1,
        )
        test2 = PytestTest(
            node_id="tests/test_foo.py::test_baz",
            outcome="failed",
            duration=0.2,
        )
        results = PytestResults(
            tests=(test1, test2),
            duration=0.3,
            exit_code=1,
        )
        assert len(results.tests) == 2
        assert results.tests[0].outcome == "passed"
        assert results.tests[1].outcome == "failed"

    def test_is_frozen(self) -> None:
        test = PytestTest(
            node_id="tests/test_foo.py::test_bar",
            outcome="passed",
            duration=0.123,
        )
        results = PytestResults(
            tests=(test,),
            duration=1.5,
            exit_code=0,
        )
        raised = False
        try:
            results.exit_code = 1  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(PytestResults, "__slots__")


class TestSyncResult:
    def test_creates_with_required_fields(self) -> None:
        result = SyncResult(
            updated=5,
            orphaned=2,
            skipped_no_file=1,
            errors=(),
        )
        assert result.updated == 5
        assert result.orphaned == 2
        assert result.skipped_no_file == 1
        assert result.errors == ()

    def test_tuple_fields_preserve_values(self) -> None:
        result = SyncResult(
            updated=0,
            orphaned=0,
            skipped_no_file=0,
            errors=("Error 1", "Error 2"),
        )
        assert result.errors == ("Error 1", "Error 2")

    def test_is_frozen(self) -> None:
        result = SyncResult(
            updated=5,
            orphaned=2,
            skipped_no_file=1,
            errors=(),
        )
        raised = False
        try:
            result.updated = 10  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SyncResult, "__slots__")


class TestRebuildResult:
    def test_creates_with_required_fields(self) -> None:
        result = RebuildResult(
            scanned=100,
            indexed=95,
            skipped=3,
            errors=(),
        )
        assert result.scanned == 100
        assert result.indexed == 95
        assert result.skipped == 3
        assert result.errors == ()

    def test_tuple_fields_preserve_values(self) -> None:
        result = RebuildResult(
            scanned=50,
            indexed=40,
            skipped=5,
            errors=("File not found", "Invalid YAML"),
        )
        assert result.errors == ("File not found", "Invalid YAML")

    def test_is_frozen(self) -> None:
        result = RebuildResult(
            scanned=100,
            indexed=95,
            skipped=3,
            errors=(),
        )
        raised = False
        try:
            result.scanned = 200  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(RebuildResult, "__slots__")


# =============================================================================
# Progress Report Models
# =============================================================================


class TestTypeProgress:
    def test_creates_with_required_fields(self) -> None:
        progress = TypeProgress(
            req_type=RequirementType.FUNCTIONAL,
            total=10,
            implemented=7,
            verified=5,
            percentage=70.0,
        )
        assert progress.req_type == RequirementType.FUNCTIONAL
        assert progress.total == 10
        assert progress.implemented == 7
        assert progress.verified == 5
        assert progress.percentage == 70.0

    def test_is_frozen(self) -> None:
        progress = TypeProgress(
            req_type=RequirementType.FUNCTIONAL,
            total=10,
            implemented=7,
            verified=5,
            percentage=70.0,
        )
        raised = False
        try:
            progress.total = 20  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(TypeProgress, "__slots__")


class TestProgressReport:
    def test_creates_with_required_fields(self) -> None:
        type_progress = TypeProgress(
            req_type=RequirementType.FUNCTIONAL,
            total=10,
            implemented=7,
            verified=5,
            percentage=70.0,
        )
        report = ProgressReport(
            spec_id="SPEC-0001",
            total_requirements=15,
            implemented_requirements=11,
            verified_requirements=8,
            overall_percentage=73.3,
            by_type=(type_progress,),
        )
        assert report.spec_id == "SPEC-0001"
        assert report.total_requirements == 15
        assert report.implemented_requirements == 11
        assert report.verified_requirements == 8
        assert report.overall_percentage == 73.3

    def test_tuple_fields_preserve_values(self) -> None:
        type_progress1 = TypeProgress(
            req_type=RequirementType.FUNCTIONAL,
            total=10,
            implemented=7,
            verified=5,
            percentage=70.0,
        )
        type_progress2 = TypeProgress(
            req_type=RequirementType.QUALITY,
            total=5,
            implemented=3,
            verified=2,
            percentage=60.0,
        )
        report = ProgressReport(
            spec_id="SPEC-0001",
            total_requirements=15,
            implemented_requirements=10,
            verified_requirements=7,
            overall_percentage=66.7,
            by_type=(type_progress1, type_progress2),
        )
        assert len(report.by_type) == 2
        assert report.by_type[0].req_type == RequirementType.FUNCTIONAL
        assert report.by_type[1].req_type == RequirementType.QUALITY

    def test_is_frozen(self) -> None:
        report = ProgressReport(
            spec_id="SPEC-0001",
            total_requirements=15,
            implemented_requirements=11,
            verified_requirements=8,
            overall_percentage=73.3,
            by_type=(),
        )
        raised = False
        try:
            report.spec_id = "SPEC-0002"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(ProgressReport, "__slots__")


# =============================================================================
# Coverage Report Models
# =============================================================================


class TestMethodCoverage:
    def test_creates_with_required_fields(self) -> None:
        coverage = MethodCoverage(
            method=SpecTestMethod.UNIT,
            total_tests=20,
            passing_tests=18,
            requirements_covered=15,
        )
        assert coverage.method == SpecTestMethod.UNIT
        assert coverage.total_tests == 20
        assert coverage.passing_tests == 18
        assert coverage.requirements_covered == 15

    def test_is_frozen(self) -> None:
        coverage = MethodCoverage(
            method=SpecTestMethod.UNIT,
            total_tests=20,
            passing_tests=18,
            requirements_covered=15,
        )
        raised = False
        try:
            coverage.total_tests = 30  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(MethodCoverage, "__slots__")


class TestTypeCoverage:
    def test_creates_with_required_fields(self) -> None:
        coverage = TypeCoverage(
            req_type=RequirementType.FUNCTIONAL,
            total_requirements=10,
            covered_requirements=8,
            coverage_percentage=80.0,
        )
        assert coverage.req_type == RequirementType.FUNCTIONAL
        assert coverage.total_requirements == 10
        assert coverage.covered_requirements == 8
        assert coverage.coverage_percentage == 80.0

    def test_is_frozen(self) -> None:
        coverage = TypeCoverage(
            req_type=RequirementType.FUNCTIONAL,
            total_requirements=10,
            covered_requirements=8,
            coverage_percentage=80.0,
        )
        raised = False
        try:
            coverage.total_requirements = 20  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(TypeCoverage, "__slots__")


class TestCoverageReport:
    def test_creates_with_required_fields(self) -> None:
        method_coverage = MethodCoverage(
            method=SpecTestMethod.UNIT,
            total_tests=20,
            passing_tests=18,
            requirements_covered=15,
        )
        type_coverage = TypeCoverage(
            req_type=RequirementType.FUNCTIONAL,
            total_requirements=10,
            covered_requirements=8,
            coverage_percentage=80.0,
        )
        req_to_tests = MappingProxyType(
            {"REQ-0001": ("TST-0001", "TST-0002"), "REQ-0002": ("TST-0003",)}
        )
        report = CoverageReport(
            spec_id="SPEC-0001",
            total_requirements=20,
            covered_requirements=16,
            overall_coverage=80.0,
            by_method=(method_coverage,),
            by_type=(type_coverage,),
            requirement_to_tests=req_to_tests,
        )
        assert report.spec_id == "SPEC-0001"
        assert report.total_requirements == 20
        assert report.covered_requirements == 16
        assert report.overall_coverage == 80.0

    def test_tuple_fields_preserve_values(self) -> None:
        method_coverage1 = MethodCoverage(
            method=SpecTestMethod.UNIT,
            total_tests=15,
            passing_tests=14,
            requirements_covered=10,
        )
        method_coverage2 = MethodCoverage(
            method=SpecTestMethod.INTEGRATION,
            total_tests=5,
            passing_tests=4,
            requirements_covered=5,
        )
        type_coverage = TypeCoverage(
            req_type=RequirementType.FUNCTIONAL,
            total_requirements=10,
            covered_requirements=8,
            coverage_percentage=80.0,
        )
        req_to_tests: MappingProxyType[str, tuple[str, ...]] = MappingProxyType({})
        report = CoverageReport(
            spec_id="SPEC-0001",
            total_requirements=20,
            covered_requirements=15,
            overall_coverage=75.0,
            by_method=(method_coverage1, method_coverage2),
            by_type=(type_coverage,),
            requirement_to_tests=req_to_tests,
        )
        assert len(report.by_method) == 2
        assert report.by_method[0].method == SpecTestMethod.UNIT
        assert report.by_method[1].method == SpecTestMethod.INTEGRATION

    def test_mapping_proxy_type_field(self) -> None:
        method_coverage = MethodCoverage(
            method=SpecTestMethod.UNIT,
            total_tests=10,
            passing_tests=10,
            requirements_covered=5,
        )
        type_coverage = TypeCoverage(
            req_type=RequirementType.FUNCTIONAL,
            total_requirements=5,
            covered_requirements=5,
            coverage_percentage=100.0,
        )
        req_to_tests = MappingProxyType(
            {
                "REQ-0001": ("TST-0001", "TST-0002"),
                "REQ-0002": ("TST-0003",),
                "REQ-0003": (),
            }
        )
        report = CoverageReport(
            spec_id="SPEC-0001",
            total_requirements=5,
            covered_requirements=5,
            overall_coverage=100.0,
            by_method=(method_coverage,),
            by_type=(type_coverage,),
            requirement_to_tests=req_to_tests,
        )
        assert isinstance(report.requirement_to_tests, MappingProxyType)
        assert report.requirement_to_tests["REQ-0001"] == ("TST-0001", "TST-0002")
        assert report.requirement_to_tests["REQ-0002"] == ("TST-0003",)
        assert report.requirement_to_tests["REQ-0003"] == ()

    def test_is_frozen(self) -> None:
        report = CoverageReport(
            spec_id="SPEC-0001",
            total_requirements=10,
            covered_requirements=8,
            overall_coverage=80.0,
            by_method=(),
            by_type=(),
            requirement_to_tests=MappingProxyType({}),
        )
        raised = False
        try:
            report.spec_id = "SPEC-0002"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(CoverageReport, "__slots__")


# =============================================================================
# Orphan Report Models
# =============================================================================


class TestOrphanReport:
    def test_creates_with_required_fields(
        self, make_test: Callable[..., SpecTest]
    ) -> None:
        orphan_test = make_test(id="TST-0001", tests_requirements=())
        report = OrphanReport(
            spec_id="SPEC-0001",
            orphaned_tests=(orphan_test,),
            orphaned_artifacts=("ART-0001",),
            tests_missing_file=(),
        )
        assert report.spec_id == "SPEC-0001"
        assert len(report.orphaned_tests) == 1
        assert report.orphaned_tests[0].id == "TST-0001"
        assert report.orphaned_artifacts == ("ART-0001",)
        assert report.tests_missing_file == ()

    def test_tuple_fields_preserve_values(
        self, make_test: Callable[..., SpecTest]
    ) -> None:
        orphan_test1 = make_test(id="TST-0001", tests_requirements=())
        orphan_test2 = make_test(id="TST-0002", tests_requirements=())
        missing_file_test = make_test(id="TST-0003", file=None, function=None)
        report = OrphanReport(
            spec_id="SPEC-0001",
            orphaned_tests=(orphan_test1, orphan_test2),
            orphaned_artifacts=("ART-0001", "ART-0002", "ART-0003"),
            tests_missing_file=(missing_file_test,),
        )
        assert len(report.orphaned_tests) == 2
        assert len(report.orphaned_artifacts) == 3
        assert len(report.tests_missing_file) == 1

    def test_is_frozen(self, make_test: Callable[..., SpecTest]) -> None:
        report = OrphanReport(
            spec_id="SPEC-0001",
            orphaned_tests=(),
            orphaned_artifacts=(),
            tests_missing_file=(),
        )
        raised = False
        try:
            report.spec_id = "SPEC-0002"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(OrphanReport, "__slots__")


# =============================================================================
# Dependency Graph Models
# =============================================================================


class TestDependencyNode:
    def test_creates_with_required_fields(self) -> None:
        node = DependencyNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        assert node.spec_id == "SPEC-0001"
        assert node.title == "Test Spec"
        assert node.status == SpecStatus.DRAFT
        assert node.depth == 0

    def test_is_frozen(self) -> None:
        node = DependencyNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        raised = False
        try:
            node.depth = 1  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(DependencyNode, "__slots__")


class TestDependencyGraph:
    def test_creates_with_required_fields(self) -> None:
        node = DependencyNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        graph = DependencyGraph(
            nodes=(node,),
            edges=(),
            roots=("SPEC-0001",),
            leaves=("SPEC-0001",),
            topological_order=("SPEC-0001",),
            has_cycles=False,
            cycle_path=(),
        )
        assert graph.nodes == (node,)
        assert graph.edges == ()
        assert graph.roots == ("SPEC-0001",)
        assert graph.leaves == ("SPEC-0001",)
        assert graph.topological_order == ("SPEC-0001",)
        assert graph.has_cycles is False
        assert graph.cycle_path == ()

    def test_tuple_fields_preserve_values(self) -> None:
        node1 = DependencyNode(
            spec_id="SPEC-0001",
            title="Spec 1",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        node2 = DependencyNode(
            spec_id="SPEC-0002",
            title="Spec 2",
            status=SpecStatus.IMPLEMENTING,
            depth=1,
        )
        graph = DependencyGraph(
            nodes=(node1, node2),
            edges=(("SPEC-0002", "SPEC-0001"),),
            roots=("SPEC-0002",),
            leaves=("SPEC-0001",),
            topological_order=("SPEC-0002", "SPEC-0001"),
            has_cycles=False,
            cycle_path=(),
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0] == ("SPEC-0002", "SPEC-0001")

    def test_with_cycles(self) -> None:
        node1 = DependencyNode(
            spec_id="SPEC-0001",
            title="Spec 1",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        node2 = DependencyNode(
            spec_id="SPEC-0002",
            title="Spec 2",
            status=SpecStatus.DRAFT,
            depth=0,
        )
        graph = DependencyGraph(
            nodes=(node1, node2),
            edges=(("SPEC-0001", "SPEC-0002"), ("SPEC-0002", "SPEC-0001")),
            roots=(),
            leaves=(),
            topological_order=(),
            has_cycles=True,
            cycle_path=("SPEC-0001", "SPEC-0002", "SPEC-0001"),
        )
        assert graph.has_cycles is True
        assert graph.cycle_path == ("SPEC-0001", "SPEC-0002", "SPEC-0001")
        assert graph.topological_order == ()

    def test_is_frozen(self) -> None:
        graph = DependencyGraph(
            nodes=(),
            edges=(),
            roots=(),
            leaves=(),
            topological_order=(),
            has_cycles=False,
            cycle_path=(),
        )
        raised = False
        try:
            graph.has_cycles = True  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(DependencyGraph, "__slots__")


# =============================================================================
# Relationship Graph Models
# =============================================================================


class TestSpecNode:
    def test_creates_with_required_fields(self) -> None:
        node = SpecNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            spec_type=SpecType.FEATURE,
            status=SpecStatus.DRAFT,
        )
        assert node.spec_id == "SPEC-0001"
        assert node.title == "Test Spec"
        assert node.spec_type == SpecType.FEATURE
        assert node.status == SpecStatus.DRAFT

    def test_is_frozen(self) -> None:
        node = SpecNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            spec_type=SpecType.FEATURE,
            status=SpecStatus.DRAFT,
        )
        raised = False
        try:
            node.title = "Modified"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(SpecNode, "__slots__")


class TestRelationshipEdge:
    def test_creates_with_required_fields(self) -> None:
        edge = RelationshipEdge(
            from_spec_id="SPEC-0001",
            to_spec_id="SPEC-0002",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        assert edge.from_spec_id == "SPEC-0001"
        assert edge.to_spec_id == "SPEC-0002"
        assert edge.relationship_type == RelationshipType.DEPENDS_ON

    def test_is_frozen(self) -> None:
        edge = RelationshipEdge(
            from_spec_id="SPEC-0001",
            to_spec_id="SPEC-0002",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        raised = False
        try:
            edge.to_spec_id = "SPEC-0003"  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(RelationshipEdge, "__slots__")


class TestRelationshipGraph:
    def test_creates_with_required_fields(self) -> None:
        node = SpecNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            spec_type=SpecType.FEATURE,
            status=SpecStatus.DRAFT,
        )
        edge = RelationshipEdge(
            from_spec_id="SPEC-0001",
            to_spec_id="SPEC-0002",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        node_index = MappingProxyType({"SPEC-0001": node})
        graph = RelationshipGraph(
            nodes=(node,),
            edges=(edge,),
            node_index=node_index,
        )
        assert graph.nodes == (node,)
        assert graph.edges == (edge,)
        assert graph.node_index == node_index

    def test_tuple_fields_preserve_values(self) -> None:
        node1 = SpecNode(
            spec_id="SPEC-0001",
            title="Spec 1",
            spec_type=SpecType.FEATURE,
            status=SpecStatus.DRAFT,
        )
        node2 = SpecNode(
            spec_id="SPEC-0002",
            title="Spec 2",
            spec_type=SpecType.SUBSYSTEM,
            status=SpecStatus.APPROVED,
        )
        edge1 = RelationshipEdge(
            from_spec_id="SPEC-0001",
            to_spec_id="SPEC-0002",
            relationship_type=RelationshipType.DEPENDS_ON,
        )
        edge2 = RelationshipEdge(
            from_spec_id="SPEC-0001",
            to_spec_id="SPEC-0002",
            relationship_type=RelationshipType.EXTENDS,
        )
        node_index = MappingProxyType({"SPEC-0001": node1, "SPEC-0002": node2})
        graph = RelationshipGraph(
            nodes=(node1, node2),
            edges=(edge1, edge2),
            node_index=node_index,
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 2
        assert graph.edges[0].relationship_type == RelationshipType.DEPENDS_ON
        assert graph.edges[1].relationship_type == RelationshipType.EXTENDS

    def test_mapping_proxy_type_field(self) -> None:
        node = SpecNode(
            spec_id="SPEC-0001",
            title="Test Spec",
            spec_type=SpecType.FEATURE,
            status=SpecStatus.DRAFT,
        )
        node_index = MappingProxyType({"SPEC-0001": node})
        graph = RelationshipGraph(
            nodes=(node,),
            edges=(),
            node_index=node_index,
        )
        assert isinstance(graph.node_index, MappingProxyType)
        assert graph.node_index["SPEC-0001"] == node

    def test_is_frozen(self) -> None:
        graph = RelationshipGraph(
            nodes=(),
            edges=(),
            node_index=MappingProxyType({}),
        )
        raised = False
        try:
            graph.nodes = ()  # pyright: ignore[reportAttributeAccessIssue]
        except AttributeError:
            raised = True
        assert raised

    def test_has_slots(self) -> None:
        assert hasattr(RelationshipGraph, "__slots__")
