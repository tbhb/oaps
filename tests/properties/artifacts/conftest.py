"""Fixtures for artifact property-based tests."""

import pytest

from oaps.artifacts._registry import ArtifactRegistry


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    """Reset the registry singleton before each test."""
    ArtifactRegistry._reset_instance()
