"""Fixtures for artifact system integration tests."""

from pathlib import Path

import pytest

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._store import ArtifactStore


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the registry singleton before each test."""
    ArtifactRegistry._reset_instance()


@pytest.fixture
def store(tmp_path: Path) -> ArtifactStore:
    """Create an initialized artifact store in a temp directory."""
    store = ArtifactStore(tmp_path)
    store.initialize()
    return store


@pytest.fixture
def populated_store(store: ArtifactStore) -> ArtifactStore:
    """Create a store with sample artifacts for testing."""
    # Add text artifacts
    store.add_artifact(
        type_prefix="DC",
        title="Architecture Decision: Use PostgreSQL",
        author="architect",
        content="# Decision\n\nWe will use PostgreSQL for the database.",
        subtype="architecture",
        tags=["database", "architecture"],
        summary="Decision to use PostgreSQL as primary database",
    )

    store.add_artifact(
        type_prefix="DC",
        title="Technology Choice: FastAPI",
        author="architect",
        content="# Decision\n\nFastAPI for the REST API.",
        subtype="technology",
        tags=["api", "python"],
    )

    store.add_artifact(
        type_prefix="AN",
        title="Performance Analysis",
        author="engineer",
        content="# Analysis\n\nPerformance requirements analysis.",
        subtype="performance",
        references=["DC-0001"],
    )

    # Add binary artifact
    store.add_artifact(
        type_prefix="IM",
        title="Architecture Diagram",
        author="architect",
        content=b"\x89PNG\r\n\x1a\n\x00\x00\x00",
        type_fields={"alt_text": "System architecture diagram showing components"},
    )

    return store
