"""Tests for artifact type registry."""

import pytest

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._types import BASE_TYPES, RESERVED_PREFIXES, TypeDefinition
from oaps.exceptions import TypeNotRegisteredError


class TestSingleton:
    def test_get_instance_returns_registry(self) -> None:
        registry = ArtifactRegistry.get_instance()
        assert isinstance(registry, ArtifactRegistry)

    def test_get_instance_returns_same_instance(self) -> None:
        registry1 = ArtifactRegistry.get_instance()
        registry2 = ArtifactRegistry.get_instance()
        assert registry1 is registry2

    def test_reset_instance_creates_new_instance(self) -> None:
        registry1 = ArtifactRegistry.get_instance()
        ArtifactRegistry._reset_instance()
        registry2 = ArtifactRegistry.get_instance()

        assert registry1 is not registry2


class TestBaseTypesLoading:
    def test_base_types_loaded_on_get_instance(self) -> None:
        registry = ArtifactRegistry.get_instance()

        assert len(registry.list_types()) >= 10

    def test_all_base_types_registered(self) -> None:
        registry = ArtifactRegistry.get_instance()

        for type_def in BASE_TYPES:
            assert registry.has_type(type_def.prefix)

    def test_get_base_types_returns_ten_types(self) -> None:
        registry = ArtifactRegistry.get_instance()
        base_types = registry.get_base_types()

        assert len(base_types) == 10


class TestHasType:
    def test_returns_true_for_registered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()
        assert registry.has_type("RV") is True

    def test_returns_false_for_unregistered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()
        assert registry.has_type("XX") is False


class TestGetType:
    def test_returns_type_definition_for_registered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()
        type_def = registry.get_type("RV")

        assert type_def is not None
        assert type_def.prefix == "RV"
        assert type_def.name == "review"

    def test_returns_none_for_unregistered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()
        assert registry.get_type("XX") is None


class TestGetTypeOrRaise:
    def test_returns_type_definition_for_registered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()
        type_def = registry.get_type_or_raise("RV")

        assert type_def.prefix == "RV"

    def test_raises_for_unregistered_type(self) -> None:
        registry = ArtifactRegistry.get_instance()

        with pytest.raises(TypeNotRegisteredError) as exc_info:
            registry.get_type_or_raise("XX")

        assert exc_info.value.prefix == "XX"


class TestListTypes:
    def test_returns_list_of_type_definitions(self) -> None:
        registry = ArtifactRegistry.get_instance()
        types = registry.list_types()

        assert isinstance(types, list)
        assert all(isinstance(t, TypeDefinition) for t in types)

    def test_returns_sorted_by_prefix(self) -> None:
        registry = ArtifactRegistry.get_instance()
        types = registry.list_types()
        prefixes = [t.prefix for t in types]

        assert prefixes == sorted(prefixes)


class TestRegisterType:
    def test_registers_custom_type(self, custom_type: TypeDefinition) -> None:
        registry = ArtifactRegistry.get_instance()
        registry.register_type(custom_type)

        assert registry.has_type("TR")
        type_def = registry.get_type("TR")
        assert type_def is not None
        assert type_def.name == "training"

    def test_custom_type_appears_in_list_types(
        self, custom_type: TypeDefinition
    ) -> None:
        registry = ArtifactRegistry.get_instance()
        registry.register_type(custom_type)
        types = registry.list_types()

        assert any(t.prefix == "TR" for t in types)

    def test_rejects_invalid_prefix_format_lowercase(self) -> None:
        registry = ArtifactRegistry.get_instance()
        invalid_type = TypeDefinition(
            prefix="tr",
            name="training",
            description="Test",
            category="text",
        )

        with pytest.raises(ValueError, match="Invalid prefix format"):
            registry.register_type(invalid_type)

    def test_rejects_invalid_prefix_format_single_char(self) -> None:
        registry = ArtifactRegistry.get_instance()
        invalid_type = TypeDefinition(
            prefix="T",
            name="training",
            description="Test",
            category="text",
        )

        with pytest.raises(ValueError, match="Invalid prefix format"):
            registry.register_type(invalid_type)

    def test_rejects_invalid_prefix_format_three_chars(self) -> None:
        registry = ArtifactRegistry.get_instance()
        invalid_type = TypeDefinition(
            prefix="TRN",
            name="training",
            description="Test",
            category="text",
        )

        with pytest.raises(ValueError, match="Invalid prefix format"):
            registry.register_type(invalid_type)

    def test_rejects_reserved_prefix(self) -> None:
        registry = ArtifactRegistry.get_instance()
        invalid_type = TypeDefinition(
            prefix="RV",  # Reserved for review
            name="custom-review",
            description="Test",
            category="text",
        )

        with pytest.raises(ValueError, match="reserved prefix"):
            registry.register_type(invalid_type)

    def test_rejects_duplicate_prefix(self, custom_type: TypeDefinition) -> None:
        registry = ArtifactRegistry.get_instance()
        registry.register_type(custom_type)

        duplicate = TypeDefinition(
            prefix="TR",
            name="tutorial",
            description="Different type",
            category="text",
        )

        with pytest.raises(ValueError, match="already registered"):
            registry.register_type(duplicate)

    def test_rejects_duplicate_name(self, custom_type: TypeDefinition) -> None:
        registry = ArtifactRegistry.get_instance()
        registry.register_type(custom_type)

        duplicate = TypeDefinition(
            prefix="TT",
            name="training",  # Same name as custom_type
            description="Different prefix",
            category="text",
        )

        with pytest.raises(ValueError, match="name already registered"):
            registry.register_type(duplicate)


class TestPrefixToTypeName:
    def test_converts_registered_prefix(self) -> None:
        registry = ArtifactRegistry.get_instance()

        assert registry.prefix_to_type_name("RV") == "review"
        assert registry.prefix_to_type_name("DC") == "decision"
        assert registry.prefix_to_type_name("IM") == "image"

    def test_returns_none_for_unknown_prefix(self) -> None:
        registry = ArtifactRegistry.get_instance()

        assert registry.prefix_to_type_name("XX") is None


class TestTypeNameToPrefix:
    def test_converts_registered_name(self) -> None:
        registry = ArtifactRegistry.get_instance()

        assert registry.type_name_to_prefix("review") == "RV"
        assert registry.type_name_to_prefix("decision") == "DC"
        assert registry.type_name_to_prefix("image") == "IM"

    def test_returns_none_for_unknown_name(self) -> None:
        registry = ArtifactRegistry.get_instance()

        assert registry.type_name_to_prefix("unknown") is None


class TestReservedPrefixesIntegrity:
    def test_cannot_override_any_reserved_prefix(self) -> None:
        registry = ArtifactRegistry.get_instance()

        for prefix in RESERVED_PREFIXES:
            custom = TypeDefinition(
                prefix=prefix,
                name=f"custom-{prefix.lower()}",
                description="Attempted override",
                category="text",
            )

            with pytest.raises(ValueError, match="reserved prefix"):
                registry.register_type(custom)
