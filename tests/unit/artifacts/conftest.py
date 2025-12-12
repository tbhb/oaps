"""Fixtures for artifact system unit tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._types import (
    Artifact,
    ArtifactMetadata,
    TypeDefinition,
    TypeField,
)


@pytest.fixture
def sample_metadata() -> ArtifactMetadata:
    """Sample artifact metadata for testing."""
    return ArtifactMetadata(
        id="RV-0001",
        type="review",
        title="Security Review",
        status="draft",
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        author="reviewer",
    )


@pytest.fixture
def sample_metadata_full() -> ArtifactMetadata:
    """Sample artifact metadata with all optional fields populated."""
    return ArtifactMetadata(
        id="RV-0001",
        type="review",
        title="Security Review of Authentication Module",
        status="complete",
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        author="security-team",
        subtype="security",
        updated=datetime(2025, 1, 20, 14, 0, tzinfo=UTC),
        reviewers=("alice", "bob"),
        references=("FR-0001", "FR-0002"),
        supersedes=None,
        superseded_by=None,
        tags=("security", "auth", "critical"),
        summary="Comprehensive security review of the authentication module.",
        type_fields={
            "review_type": "security",
            "findings": 5,
            "severity": "high",
        },
    )


@pytest.fixture
def sample_artifact(tmp_path: Path) -> Artifact:
    """Sample text artifact for testing."""
    file_path = tmp_path / "artifacts" / "20250115103000-RV-0001-security-review.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("""---
id: RV-0001
type: review
title: Security Review
status: draft
created: 2025-01-15T10:30:00+00:00
author: reviewer
---

# Security Review

Content here.
""")

    return Artifact(
        id="RV-0001",
        type="review",
        title="Security Review",
        status="draft",
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        author="reviewer",
        file_path=file_path,
    )


@pytest.fixture
def sample_binary_artifact(tmp_path: Path) -> Artifact:
    """Sample binary artifact with sidecar metadata."""
    file_path = tmp_path / "artifacts" / "20250115103000-IM-0001-screenshot.png"
    metadata_path = file_path.with_suffix(".png.metadata.yaml")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Create dummy binary file
    file_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    # Create sidecar metadata
    metadata_path.write_text("""id: IM-0001
type: image
title: Error Screenshot
status: complete
created: 2025-01-15T10:30:00+00:00
author: developer
alt_text: Screenshot showing error message
""")

    return Artifact(
        id="IM-0001",
        type="image",
        title="Error Screenshot",
        status="complete",
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        author="developer",
        file_path=file_path,
        metadata_file_path=metadata_path,
        type_fields={"alt_text": "Screenshot showing error message"},
    )


@pytest.fixture
def custom_type() -> TypeDefinition:
    """Custom artifact type for testing registration."""
    return TypeDefinition(
        prefix="TR",
        name="training",
        description="Training materials",
        category="text",
        subtypes=("module", "quiz", "exercise"),
        type_fields=(
            TypeField(
                name="level",
                field_type="string",
                description="Difficulty level",
                allowed_values=("beginner", "intermediate", "advanced"),
            ),
        ),
    )


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the registry singleton before each test.

    This ensures tests don't affect each other through the global registry.
    """
    ArtifactRegistry._reset_instance()
