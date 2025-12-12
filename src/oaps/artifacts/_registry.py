"""Artifact type registry.

This module provides the ArtifactRegistry class for managing artifact type
definitions. The registry uses a singleton pattern with thread-safe
initialization to ensure consistent type definitions across all stores
in a process.

Example:
    >>> from oaps.artifacts import ArtifactRegistry
    >>> registry = ArtifactRegistry.get_instance()
    >>> registry.has_type("RV")
    True
    >>> type_def = registry.get_type("RV")
    >>> type_def.name
    'review'
"""

import re
import threading
from typing import ClassVar

from oaps.artifacts._types import BASE_TYPES, RESERVED_PREFIXES, TypeDefinition
from oaps.exceptions import TypeNotRegisteredError

# Pattern for valid prefixes: exactly 2 uppercase letters
_PREFIX_PATTERN = re.compile(r"^[A-Z]{2}$")


class ArtifactRegistry:
    """Thread-safe singleton registry for artifact type definitions.

    The registry maintains a mapping of type prefixes (e.g., "RV", "DC") to
    their TypeDefinition objects. Base types are loaded on first instance
    creation. Custom types can be registered for project-specific needs.

    Use get_instance() to obtain the singleton instance. Do not instantiate
    directly.

    Attributes:
        _instance: Class-level singleton instance.
        _lock: Class-level lock for thread-safe initialization.

    Example:
        >>> registry = ArtifactRegistry.get_instance()
        >>> registry.list_types()  # Returns all registered types
        [TypeDefinition(prefix='AN', ...), ...]
    """

    _instance: ClassVar[ArtifactRegistry | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    __slots__ = ("_name_to_prefix", "_types")

    def __init__(self) -> None:
        """Initialize registry with empty type mappings.

        Note:
            Do not call directly. Use get_instance() instead.
        """
        self._types: dict[str, TypeDefinition] = {}
        self._name_to_prefix: dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> ArtifactRegistry:
        """Get the global registry instance (singleton).

        Thread-safe using double-checked locking pattern.

        Returns:
            The singleton ArtifactRegistry instance with base types loaded.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> registry is ArtifactRegistry.get_instance()
            True
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._load_base_types()
                    cls._instance = instance
        # After the lock, _instance is guaranteed to be set
        result = cls._instance
        assert result is not None  # noqa: S101
        return result

    @classmethod
    def _reset_instance(cls) -> None:
        """Reset the singleton instance (for testing only).

        Warning:
            This method is intended for test cleanup only. Do not use in
            production code.
        """
        with cls._lock:
            cls._instance = None

    def _load_base_types(self) -> None:
        """Load all base types into the registry.

        Called during singleton initialization.
        """
        for type_def in BASE_TYPES:
            self._types[type_def.prefix] = type_def
            self._name_to_prefix[type_def.name] = type_def.prefix

    def register_type(self, type_def: TypeDefinition) -> None:
        """Register a custom artifact type.

        Args:
            type_def: Type definition to register.

        Raises:
            ValueError: If prefix format is invalid (not 2 uppercase letters).
            ValueError: If prefix is already registered (reserved or custom).

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> custom = TypeDefinition(
            ...     prefix="TR",
            ...     name="training",
            ...     description="Training materials",
            ...     category="text",
            ... )
            >>> registry.register_type(custom)
        """
        prefix = type_def.prefix

        # Validate prefix format
        if not _PREFIX_PATTERN.match(prefix):
            msg = f"Invalid prefix format: {prefix!r} (expected two uppercase letters)"
            raise ValueError(msg)

        # Check if prefix is already registered
        if prefix in self._types:
            if prefix in RESERVED_PREFIXES:
                msg = f"Cannot register type with reserved prefix: {prefix!r}"
            else:
                msg = f"Type prefix already registered: {prefix!r}"
            raise ValueError(msg)

        # Check if name is already used
        if type_def.name in self._name_to_prefix:
            msg = f"Type name already registered: {type_def.name!r}"
            raise ValueError(msg)

        self._types[prefix] = type_def
        self._name_to_prefix[type_def.name] = prefix

    def has_type(self, prefix: str) -> bool:
        """Check if a type is registered.

        Args:
            prefix: Two-letter type prefix.

        Returns:
            True if type is registered.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> registry.has_type("RV")
            True
            >>> registry.has_type("XX")
            False
        """
        return prefix in self._types

    def get_type(self, prefix: str) -> TypeDefinition | None:
        """Get type definition by prefix.

        Args:
            prefix: Two-letter type prefix.

        Returns:
            Type definition or None if not found.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> type_def = registry.get_type("RV")
            >>> type_def.name
            'review'
        """
        return self._types.get(prefix)

    def get_type_or_raise(self, prefix: str) -> TypeDefinition:
        """Get type definition by prefix, raising if not found.

        Args:
            prefix: Two-letter type prefix.

        Returns:
            Type definition.

        Raises:
            TypeNotRegisteredError: If type is not registered.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> type_def = registry.get_type_or_raise("RV")
            >>> type_def.name
            'review'
        """
        type_def = self._types.get(prefix)
        if type_def is None:
            msg = f"Type not registered: {prefix!r}"
            raise TypeNotRegisteredError(msg, prefix=prefix)
        return type_def

    def list_types(self) -> list[TypeDefinition]:
        """List all registered types.

        Returns:
            List of type definitions, sorted by prefix.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> types = registry.list_types()
            >>> [t.prefix for t in types[:3]]
            ['AN', 'CH', 'DC']
        """
        return sorted(self._types.values(), key=lambda t: t.prefix)

    def get_base_types(self) -> list[TypeDefinition]:
        """Get base types defined by the artifact system.

        Returns:
            List of base type definitions (10 types).

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> base = registry.get_base_types()
            >>> len(base)
            10
        """
        return [self._types[prefix] for prefix in sorted(RESERVED_PREFIXES)]

    def prefix_to_type_name(self, prefix: str) -> str | None:
        """Convert prefix to type name.

        Args:
            prefix: Two-letter prefix (e.g., "RV").

        Returns:
            Type name (e.g., "review") or None if not found.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> registry.prefix_to_type_name("RV")
            'review'
        """
        type_def = self._types.get(prefix)
        return type_def.name if type_def else None

    def type_name_to_prefix(self, type_name: str) -> str | None:
        """Convert type name to prefix.

        Args:
            type_name: Type name (e.g., "review").

        Returns:
            Two-letter prefix (e.g., "RV") or None if not found.

        Example:
            >>> registry = ArtifactRegistry.get_instance()
            >>> registry.type_name_to_prefix("review")
            'RV'
        """
        return self._name_to_prefix.get(type_name)
