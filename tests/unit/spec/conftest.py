from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from oaps.spec._models import (
    Artifact,
    ArtifactStatus,
    ArtifactType,
    HistoryEntry,
    Requirement,
    RequirementStatus,
    RequirementType,
    SpecMetadata,
    SpecStatus,
    SpecSummary,
    SpecType,
    Test as SpecTest,
    TestMethod as SpecTestMethod,
    TestStatus as SpecTestStatus,
)


@pytest.fixture
def sample_datetime() -> datetime:
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)


@pytest.fixture
def make_spec_summary(
    sample_datetime: datetime,
) -> Callable[..., SpecSummary]:
    def _make(**overrides: object) -> SpecSummary:
        defaults: dict[str, object] = {
            "id": "SPEC-0001",
            "slug": "test-spec",
            "title": "Test Specification",
            "spec_type": SpecType.FEATURE,
            "status": SpecStatus.DRAFT,
            "created": sample_datetime,
            "updated": sample_datetime,
            "depends_on": (),
            "tags": (),
        }
        defaults.update(overrides)
        return SpecSummary(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


@pytest.fixture
def make_spec_metadata(
    sample_datetime: datetime,
) -> Callable[..., SpecMetadata]:
    def _make(**overrides: object) -> SpecMetadata:
        defaults: dict[str, object] = {
            "id": "SPEC-0001",
            "slug": "test-spec",
            "title": "Test Specification",
            "spec_type": SpecType.FEATURE,
            "status": SpecStatus.DRAFT,
            "created": sample_datetime,
            "updated": sample_datetime,
        }
        defaults.update(overrides)
        return SpecMetadata(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


@pytest.fixture
def make_requirement(
    sample_datetime: datetime,
) -> Callable[..., Requirement]:
    def _make(**overrides: object) -> Requirement:
        defaults: dict[str, object] = {
            "id": "REQ-0001",
            "title": "Test Requirement",
            "req_type": RequirementType.FUNCTIONAL,
            "status": RequirementStatus.PROPOSED,
            "created": sample_datetime,
            "updated": sample_datetime,
            "author": "test-author",
            "description": "Test requirement description",
        }
        defaults.update(overrides)
        return Requirement(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


@pytest.fixture
def make_test(
    sample_datetime: datetime,
) -> Callable[..., SpecTest]:
    def _make(**overrides: object) -> SpecTest:
        defaults: dict[str, object] = {
            "id": "TST-0001",
            "title": "Test Case",
            "method": SpecTestMethod.UNIT,
            "status": SpecTestStatus.PENDING,
            "created": sample_datetime,
            "updated": sample_datetime,
            "author": "test-author",
            "tests_requirements": ("REQ-0001",),
        }
        defaults.update(overrides)
        return SpecTest(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


@pytest.fixture
def make_artifact(
    sample_datetime: datetime,
) -> Callable[..., Artifact]:
    def _make(**overrides: object) -> Artifact:
        defaults: dict[str, object] = {
            "id": "RV-0001",
            "artifact_type": ArtifactType.REVIEW,
            "title": "Test Artifact",
            "status": ArtifactStatus.DRAFT,
            "created": sample_datetime,
            "updated": sample_datetime,
            "author": "test-author",
            "file_path": "artifacts/RV-0001.md",
        }
        defaults.update(overrides)
        return Artifact(**defaults)  # pyright: ignore[reportArgumentType]

    return _make


@pytest.fixture
def make_history_entry(
    sample_datetime: datetime,
) -> Callable[..., HistoryEntry]:
    def _make(**overrides: object) -> HistoryEntry:
        defaults: dict[str, object] = {
            "timestamp": sample_datetime,
            "event": "spec_created",
            "actor": "test-actor",
        }
        defaults.update(overrides)
        return HistoryEntry(**defaults)  # pyright: ignore[reportArgumentType]

    return _make
