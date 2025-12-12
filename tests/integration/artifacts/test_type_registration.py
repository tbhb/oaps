"""Integration tests for custom type registration workflows."""

from pathlib import Path

import pytest

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._store import ArtifactStore
from oaps.artifacts._types import TypeDefinition, TypeField


class TestCustomTypeRegistration:
    def test_registers_and_uses_custom_type(self, tmp_path: Path) -> None:
        # Register a custom type
        registry = ArtifactRegistry.get_instance()
        custom_type = TypeDefinition(
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
                TypeField(
                    name="duration_minutes",
                    field_type="integer",
                    description="Estimated duration",
                ),
            ),
            template="training.md",
        )
        registry.register_type(custom_type)

        # Create store with the registry
        store = ArtifactStore(tmp_path, registry=registry)
        store.initialize()

        # Create artifact with custom type
        artifact = store.add_artifact(
            type_prefix="TR",
            title="Python Basics",
            author="trainer",
            content="# Python Basics\n\nIntroduction to Python.",
            subtype="module",
            type_fields={
                "level": "beginner",
                "duration_minutes": 30,
            },
        )

        assert artifact.id == "TR-0001"
        assert artifact.type == "training"
        assert artifact.subtype == "module"

    def test_validates_custom_type_fields(self, tmp_path: Path) -> None:
        registry = ArtifactRegistry.get_instance()
        custom_type = TypeDefinition(
            prefix="TR",
            name="training",
            description="Training materials",
            category="text",
            type_fields=(
                TypeField(
                    name="level",
                    field_type="string",
                    description="Difficulty level",
                    required=True,
                    allowed_values=("beginner", "intermediate", "advanced"),
                ),
            ),
        )
        registry.register_type(custom_type)

        store = ArtifactStore(tmp_path, registry=registry)
        store.initialize()

        # Should fail validation - missing required field
        from oaps.exceptions import ArtifactValidationError

        with pytest.raises(ArtifactValidationError, match="level"):
            store.add_artifact(
                type_prefix="TR",
                title="Test",
                author="trainer",
            )

    def test_validates_custom_type_allowed_values(self, tmp_path: Path) -> None:
        registry = ArtifactRegistry.get_instance()
        custom_type = TypeDefinition(
            prefix="TR",
            name="training",
            description="Training materials",
            category="text",
            type_fields=(
                TypeField(
                    name="level",
                    field_type="string",
                    description="Difficulty level",
                    allowed_values=("beginner", "intermediate", "advanced"),
                ),
            ),
        )
        registry.register_type(custom_type)

        store = ArtifactStore(tmp_path, registry=registry)
        store.initialize()

        from oaps.exceptions import ArtifactValidationError

        with pytest.raises(ArtifactValidationError, match="Invalid value"):
            store.add_artifact(
                type_prefix="TR",
                title="Test",
                author="trainer",
                type_fields={"level": "expert"},  # Not in allowed_values
            )

    def test_custom_binary_type(self, tmp_path: Path) -> None:
        registry = ArtifactRegistry.get_instance()
        custom_binary_type = TypeDefinition(
            prefix="AU",
            name="audio",
            description="Audio recordings",
            category="binary",
            subtypes=("podcast", "narration", "music"),
            type_fields=(
                TypeField(
                    name="duration_seconds",
                    field_type="integer",
                    description="Duration in seconds",
                ),
                TypeField(
                    name="transcript",
                    field_type="string",
                    description="Path to transcript file",
                ),
            ),
            formats=("mp3", "wav", "ogg"),
        )
        registry.register_type(custom_binary_type)

        store = ArtifactStore(tmp_path, registry=registry)
        store.initialize()

        artifact = store.add_artifact(
            type_prefix="AU",
            title="Welcome Episode",
            author="host",
            content=b"fake audio data",
            subtype="podcast",
            type_fields={
                "duration_seconds": 120,
            },
        )

        assert artifact.id == "AU-0001"
        assert artifact.is_binary
        assert artifact.metadata_file_path is not None


class TestTypeRegistrationPersistence:
    def test_custom_types_persist_across_store_instances(self, tmp_path: Path) -> None:
        # Register custom type and create artifact
        registry = ArtifactRegistry.get_instance()
        registry.register_type(
            TypeDefinition(
                prefix="TR",
                name="training",
                description="Training materials",
                category="text",
            )
        )

        store1 = ArtifactStore(tmp_path, registry=registry)
        store1.initialize()
        store1.add_artifact(
            type_prefix="TR",
            title="Test Training",
            author="trainer",
        )

        # Create new store instance (same registry)
        store2 = ArtifactStore(tmp_path, registry=registry)

        # Should be able to read the artifact
        artifact = store2.get_artifact("TR-0001")
        assert artifact is not None
        assert artifact.type == "training"

        # Should be able to add more
        artifact2 = store2.add_artifact(
            type_prefix="TR",
            title="Another Training",
            author="trainer",
        )
        assert artifact2.id == "TR-0002"


class TestMixedTypesWorkflow:
    def test_works_with_base_and_custom_types(self, tmp_path: Path) -> None:
        registry = ArtifactRegistry.get_instance()
        registry.register_type(
            TypeDefinition(
                prefix="TR",
                name="training",
                description="Training materials",
                category="text",
            )
        )

        store = ArtifactStore(tmp_path, registry=registry)
        store.initialize()

        # Add base type
        dc = store.add_artifact(
            type_prefix="DC",
            title="Architecture Decision",
            author="architect",
        )

        # Add custom type
        tr = store.add_artifact(
            type_prefix="TR",
            title="Onboarding Training",
            author="trainer",
        )

        # Both should work
        assert dc.id == "DC-0001"
        assert tr.id == "TR-0001"

        # Both should be in index
        index = store.get_index()
        assert index.count == 2

        # Each has its own sequence
        dc2 = store.add_artifact(
            type_prefix="DC",
            title="Another Decision",
            author="architect",
        )
        assert dc2.id == "DC-0002"
