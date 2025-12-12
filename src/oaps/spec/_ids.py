"""ID generation and validation utilities for the OAPS specification system.

This module provides functions for generating and validating identifiers for
specifications, requirements, tests, artifacts, and cross-references.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.config import SpecConfiguration, SpecNumberingConfiguration
    from oaps.spec._models import RequirementType, TestMethod

# =============================================================================
# Dataclasses
# =============================================================================


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of an ID validation operation.

    Attributes:
        is_valid: Whether the ID passed validation.
        error_message: Human-readable error message if validation failed.
        parsed_components: Parsed ID components if validation succeeded.
    """

    is_valid: bool
    error_message: str | None = None
    parsed_components: dict[str, str | int | None] | None = None


@dataclass(frozen=True, slots=True)
class CrossReference:
    """Parsed cross-reference between specifications.

    Attributes:
        spec_id: The specification ID (e.g., "0001").
        entity_prefix: The entity type prefix (e.g., "FR").
        entity_number: The entity number.
        sub_number: Optional sub-entity number for sub-requirements.
    """

    spec_id: str
    entity_prefix: str
    entity_number: int
    sub_number: int | None = None


@dataclass(frozen=True, slots=True)
class ParsedID:
    """Parsed components of a prefixed ID.

    Attributes:
        prefix: The two-letter type prefix (e.g., "FR", "UT").
        number: The numeric portion of the ID.
        sub_number: Optional sub-number for sub-requirements.
    """

    prefix: str
    number: int
    sub_number: int | None = None


# =============================================================================
# Pattern Factory
# =============================================================================


class _PatternFactory:
    """Factory for building and caching regex patterns from configuration.

    This class builds regex patterns based on the spec configuration and caches
    them for efficient reuse.

    Attributes:
        config: The specification configuration to build patterns from.
    """

    _config: SpecConfiguration
    _spec_id_pattern: re.Pattern[str] | None
    _prefixed_id_pattern: re.Pattern[str] | None
    _sub_requirement_pattern: re.Pattern[str] | None
    _cross_reference_pattern: re.Pattern[str] | None

    def __init__(self, config: SpecConfiguration) -> None:
        """Initialize the pattern factory.

        Args:
            config: The specification configuration.
        """
        self._config = config
        self._spec_id_pattern = None
        self._prefixed_id_pattern = None
        self._sub_requirement_pattern = None
        self._cross_reference_pattern = None

    @property
    def spec_id_pattern(self) -> re.Pattern[str]:
        r"""Pattern for spec IDs: ^(\d{N})$ where N = config.numbering.digits."""
        if self._spec_id_pattern is None:
            digits = self._config.numbering.digits
            self._spec_id_pattern = re.compile(rf"^(\d{{{digits}}})$")
        return self._spec_id_pattern

    @property
    def prefixed_id_pattern(self) -> re.Pattern[str]:
        r"""Pattern for prefixed IDs: ^([A-Z]{2})-(\d{N})$."""
        if self._prefixed_id_pattern is None:
            digits = self._config.numbering.digits
            self._prefixed_id_pattern = re.compile(rf"^([A-Z]{{2}})-(\d{{{digits}}})$")
        return self._prefixed_id_pattern

    @property
    def sub_requirement_pattern(self) -> re.Pattern[str]:
        r"""Pattern for sub-requirements: ^([A-Z]{2})-(\d{N})SEP(\d{N})$."""
        if self._sub_requirement_pattern is None:
            digits = self._config.numbering.digits
            sep = re.escape(self._config.numbering.sub_separator)
            self._sub_requirement_pattern = re.compile(
                rf"^([A-Z]{{2}})-(\d{{{digits}}}){sep}(\d{{{digits}}})$"
            )
        return self._sub_requirement_pattern

    @property
    def cross_reference_pattern(self) -> re.Pattern[str]:
        r"""Pattern for cross-references.

        Format: ^(\d{N}):([A-Z]{2})-(\d{N})(?:SEP(\d{N}))?$
        """
        if self._cross_reference_pattern is None:
            digits = self._config.numbering.digits
            sep = re.escape(self._config.numbering.sub_separator)
            pattern = (
                rf"^(\d{{{digits}}}):([A-Z]{{2}})-(\d{{{digits}}})"
                rf"(?:{sep}(\d{{{digits}}}))?$"
            )
            self._cross_reference_pattern = re.compile(pattern)
        return self._cross_reference_pattern

    @property
    def requirement_prefixes(self) -> set[str]:
        """Set of all valid requirement prefixes."""
        prefixes = self._config.prefixes.requirements
        return {
            prefixes.functional,
            prefixes.quality,
            prefixes.security,
            prefixes.accessibility,
            prefixes.interface,
            prefixes.documentation,
            prefixes.constraint,
        }

    @property
    def test_prefixes(self) -> set[str]:
        """Set of all valid test prefixes."""
        prefixes = self._config.prefixes.tests
        return {
            prefixes.unit,
            prefixes.integration,
            prefixes.e2e,
            prefixes.performance,
            prefixes.conformance,
            prefixes.accessibility,
            prefixes.smoke,
            prefixes.manual,
            prefixes.fuzz,
            prefixes.property,
        }

    @property
    def artifact_prefixes(self) -> set[str]:
        """Set of all valid artifact prefixes."""
        prefixes = self._config.prefixes.artifacts
        return {
            prefixes.review,
            prefixes.change,
            prefixes.analysis,
            prefixes.decision,
            prefixes.diagram,
            prefixes.example,
            prefixes.mockup,
            prefixes.image,
            prefixes.video,
        }

    @property
    def all_prefixes(self) -> set[str]:
        """Set of all valid prefixes (requirements + tests + artifacts)."""
        return self.requirement_prefixes | self.test_prefixes | self.artifact_prefixes


# =============================================================================
# Helper Functions
# =============================================================================


def _get_requirement_prefix(
    req_type: RequirementType, config: SpecConfiguration
) -> str:
    """Get the prefix for a requirement type.

    Args:
        req_type: The requirement type.
        config: The specification configuration.

    Returns:
        The two-letter prefix for the requirement type.

    Raises:
        ValueError: If the requirement type is not valid.
    """
    requirements = config.prefixes.requirements
    prefix_map: dict[str, str] = {
        "functional": requirements.functional,
        "quality": requirements.quality,
        "security": requirements.security,
        "accessibility": requirements.accessibility,
        "interface": requirements.interface,
        "documentation": requirements.documentation,
        "constraint": requirements.constraint,
    }
    if req_type.value not in prefix_map:
        msg = f"Unknown requirement type: {req_type.value}"
        raise ValueError(msg)
    return prefix_map[req_type.value]


def _get_test_prefix(method: TestMethod, config: SpecConfiguration) -> str:
    """Get the prefix for a test method.

    Args:
        method: The test method.
        config: The specification configuration.

    Returns:
        The two-letter prefix for the test method.

    Raises:
        ValueError: If the test method is not valid.
    """
    tests = config.prefixes.tests
    prefix_map: dict[str, str] = {
        "unit": tests.unit,
        "integration": tests.integration,
        "e2e": tests.e2e,
        "performance": tests.performance,
        "conformance": tests.conformance,
        "accessibility": tests.accessibility,
        "smoke": tests.smoke,
        "manual": tests.manual,
        "fuzz": tests.fuzz,
        "property": tests.property,
    }
    if method.value not in prefix_map:
        msg = f"Unknown test method: {method.value}"
        raise ValueError(msg)
    return prefix_map[method.value]


def _get_artifact_prefix(artifact_type: str, config: SpecConfiguration) -> str:
    """Get the prefix for an artifact type.

    Args:
        artifact_type: The artifact type name (e.g., "review", "decision").
        config: The specification configuration.

    Returns:
        The two-letter prefix for the artifact type.

    Raises:
        ValueError: If the artifact type is not valid.
    """
    artifacts = config.prefixes.artifacts
    prefix_map: dict[str, str] = {
        "review": artifacts.review,
        "change": artifacts.change,
        "analysis": artifacts.analysis,
        "decision": artifacts.decision,
        "diagram": artifacts.diagram,
        "example": artifacts.example,
        "mockup": artifacts.mockup,
        "image": artifacts.image,
        "video": artifacts.video,
    }
    if artifact_type not in prefix_map:
        msg = f"Unknown artifact type: {artifact_type}"
        raise ValueError(msg)
    return prefix_map[artifact_type]


def _format_number(number: int, digits: int) -> str:
    """Format a number with zero-padding.

    Args:
        number: The number to format.
        digits: The number of digits to pad to.

    Returns:
        The zero-padded number string.
    """
    return f"{number:0{digits}d}"


def _max_id_value(digits: int) -> int:
    """Calculate the maximum ID value for a given digit count.

    Args:
        digits: The number of digits.

    Returns:
        The maximum value (10^digits - 1).
    """
    # Calculate 10^digits - 1 using multiplication to avoid Any type from **
    result = 1
    for _ in range(digits):
        result *= 10
    return result - 1


# =============================================================================
# Generation Functions
# =============================================================================


def next_spec_id(existing_ids: set[str], config: SpecNumberingConfiguration) -> str:
    """Generate the next available specification ID.

    Args:
        existing_ids: Set of existing spec IDs.
        config: The numbering configuration.

    Returns:
        The next available spec ID.

    Raises:
        ValueError: If the maximum ID has been reached.
    """
    digits: int = config.digits
    max_value = _max_id_value(digits)

    if not existing_ids:
        return _format_number(1, config.digits)

    # Parse existing IDs and find the maximum
    max_num = 0
    pattern = re.compile(rf"^(\d{{{config.digits}}})$")
    for id_str in existing_ids:
        match = pattern.match(id_str)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    next_num = max_num + 1
    if next_num > max_value:
        msg = f"Maximum spec ID reached: {_format_number(max_value, config.digits)}"
        raise ValueError(msg)

    return _format_number(next_num, config.digits)


def next_requirement_id(
    spec_id: str,
    req_type: RequirementType,
    existing: set[str],
    config: SpecConfiguration,
) -> str:
    """Generate the next available requirement ID.

    Args:
        spec_id: The specification ID (unused but kept for API consistency).
        req_type: The requirement type.
        existing: Set of existing requirement IDs.
        config: The specification configuration.

    Returns:
        The next available requirement ID in PREFIX-NNNN format.

    Raises:
        ValueError: If the maximum ID has been reached.
    """
    _ = spec_id  # Unused, kept for API consistency
    prefix = _get_requirement_prefix(req_type, config)
    return _next_prefixed_id(prefix, existing, config.numbering)


def next_test_id(
    spec_id: str,
    method: TestMethod,
    existing: set[str],
    config: SpecConfiguration,
) -> str:
    """Generate the next available test ID.

    Args:
        spec_id: The specification ID (unused but kept for API consistency).
        method: The test method.
        existing: Set of existing test IDs.
        config: The specification configuration.

    Returns:
        The next available test ID in PREFIX-NNNN format.

    Raises:
        ValueError: If the maximum ID has been reached.
    """
    _ = spec_id  # Unused, kept for API consistency
    prefix = _get_test_prefix(method, config)
    return _next_prefixed_id(prefix, existing, config.numbering)


def next_artifact_id(
    spec_id: str,
    artifact_type: str,
    existing: set[str],
    config: SpecConfiguration,
) -> str:
    """Generate the next available artifact ID.

    Args:
        spec_id: The specification ID (unused but kept for API consistency).
        artifact_type: The artifact type name (e.g., "review", "decision").
        existing: Set of existing artifact IDs.
        config: The specification configuration.

    Returns:
        The next available artifact ID in PREFIX-NNNN format.

    Raises:
        ValueError: If the maximum ID has been reached.
        AttributeError: If the artifact type is not valid.
    """
    _ = spec_id  # Unused, kept for API consistency
    prefix = _get_artifact_prefix(artifact_type, config)
    return _next_prefixed_id(prefix, existing, config.numbering)


def next_sub_requirement_id(
    parent_id: str,
    existing: set[str],
    config: SpecNumberingConfiguration,
) -> str:
    """Generate the next available sub-requirement ID.

    Args:
        parent_id: The parent requirement ID (PREFIX-NNNN format).
        existing: Set of existing requirement IDs.
        config: The numbering configuration.

    Returns:
        The next available sub-requirement ID in PREFIX-NNNN.MMMM format.

    Raises:
        ValueError: If the parent ID is invalid or maximum sub-ID reached.
    """
    # Parse parent ID
    pattern = re.compile(rf"^([A-Z]{{2}})-(\d{{{config.digits}}})$")
    match = pattern.match(parent_id)
    if not match:
        msg = f"Invalid parent ID format: {parent_id}"
        raise ValueError(msg)

    prefix = match.group(1)
    parent_num = match.group(2)
    sep = config.sub_separator
    digits: int = config.digits
    max_value = _max_id_value(digits)

    # Find existing sub-requirements for this parent
    sub_pattern_str = (
        rf"^{re.escape(prefix)}-{re.escape(parent_num)}{re.escape(sep)}"
        rf"(\d{{{config.digits}}})$"
    )
    sub_pattern = re.compile(sub_pattern_str)

    max_sub = 0
    for id_str in existing:
        sub_match = sub_pattern.match(id_str)
        if sub_match:
            sub_num = int(sub_match.group(1))
            max_sub = max(max_sub, sub_num)

    next_sub = max_sub + 1
    if next_sub > max_value:
        msg = f"Maximum sub-requirement ID reached for {parent_id}"
        raise ValueError(msg)

    return f"{prefix}-{parent_num}{sep}{_format_number(next_sub, config.digits)}"


def _next_prefixed_id(
    prefix: str,
    existing: set[str],
    config: SpecNumberingConfiguration,
) -> str:
    """Generate the next available ID for a given prefix.

    Args:
        prefix: The two-letter prefix.
        existing: Set of existing IDs.
        config: The numbering configuration.

    Returns:
        The next available ID in PREFIX-NNNN format.

    Raises:
        ValueError: If the maximum ID has been reached.
    """
    digits: int = config.digits
    max_value = _max_id_value(digits)
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d{{{digits}}})$")

    max_num = 0
    for id_str in existing:
        match = pattern.match(id_str)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    next_num = max_num + 1
    if next_num > max_value:
        max_id = f"{prefix}-{_format_number(max_value, digits)}"
        msg = f"Maximum ID reached for prefix {prefix}: {max_id}"
        raise ValueError(msg)

    return f"{prefix}-{_format_number(next_num, digits)}"


# =============================================================================
# Validation Functions
# =============================================================================


def validate_spec_id(
    id_str: str, config: SpecNumberingConfiguration
) -> ValidationResult:
    """Validate a specification ID.

    Args:
        id_str: The ID string to validate.
        config: The numbering configuration.

    Returns:
        ValidationResult with is_valid, error_message, and parsed_components.
    """
    pattern = re.compile(rf"^(\d{{{config.digits}}})$")
    match = pattern.match(id_str)

    if not match:
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Invalid spec ID format: expected {config.digits} digits, "
                f"got '{id_str}'"
            ),
        )

    return ValidationResult(
        is_valid=True,
        parsed_components={"number": int(match.group(1))},
    )


def validate_requirement_id(id_str: str, config: SpecConfiguration) -> ValidationResult:
    """Validate a requirement ID.

    Args:
        id_str: The ID string to validate.
        config: The specification configuration.

    Returns:
        ValidationResult with is_valid, error_message, and parsed_components.
    """
    factory = _PatternFactory(config)

    # Try sub-requirement pattern first
    sub_match = factory.sub_requirement_pattern.match(id_str)
    if sub_match:
        prefix = sub_match.group(1)
        if prefix not in factory.requirement_prefixes:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid requirement prefix: '{prefix}'",
            )
        return ValidationResult(
            is_valid=True,
            parsed_components={
                "prefix": prefix,
                "number": int(sub_match.group(2)),
                "sub_number": int(sub_match.group(3)),
            },
        )

    # Try standard prefixed ID pattern
    match = factory.prefixed_id_pattern.match(id_str)
    if not match:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid requirement ID format: '{id_str}'",
        )

    prefix = match.group(1)
    if prefix not in factory.requirement_prefixes:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid requirement prefix: '{prefix}'",
        )

    return ValidationResult(
        is_valid=True,
        parsed_components={
            "prefix": prefix,
            "number": int(match.group(2)),
            "sub_number": None,
        },
    )


def validate_test_id(id_str: str, config: SpecConfiguration) -> ValidationResult:
    """Validate a test ID.

    Args:
        id_str: The ID string to validate.
        config: The specification configuration.

    Returns:
        ValidationResult with is_valid, error_message, and parsed_components.
    """
    factory = _PatternFactory(config)

    match = factory.prefixed_id_pattern.match(id_str)
    if not match:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid test ID format: '{id_str}'",
        )

    prefix = match.group(1)
    if prefix not in factory.test_prefixes:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid test prefix: '{prefix}'",
        )

    return ValidationResult(
        is_valid=True,
        parsed_components={
            "prefix": prefix,
            "number": int(match.group(2)),
            "sub_number": None,
        },
    )


def validate_artifact_id(id_str: str, config: SpecConfiguration) -> ValidationResult:
    """Validate an artifact ID.

    Args:
        id_str: The ID string to validate.
        config: The specification configuration.

    Returns:
        ValidationResult with is_valid, error_message, and parsed_components.
    """
    factory = _PatternFactory(config)

    match = factory.prefixed_id_pattern.match(id_str)
    if not match:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid artifact ID format: '{id_str}'",
        )

    prefix = match.group(1)
    if prefix not in factory.artifact_prefixes:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid artifact prefix: '{prefix}'",
        )

    return ValidationResult(
        is_valid=True,
        parsed_components={
            "prefix": prefix,
            "number": int(match.group(2)),
            "sub_number": None,
        },
    )


def validate_cross_reference(ref: str, config: SpecConfiguration) -> ValidationResult:
    """Validate a cross-reference string.

    Cross-references have the format: NNNN:PREFIX-NNNN[.NNNN]

    Args:
        ref: The cross-reference string to validate.
        config: The specification configuration.

    Returns:
        ValidationResult with is_valid, error_message, and parsed_components.
    """
    factory = _PatternFactory(config)

    match = factory.cross_reference_pattern.match(ref)
    if not match:
        return ValidationResult(
            is_valid=False,
            error_message=f"Invalid cross-reference format: '{ref}'",
        )

    spec_id = match.group(1)
    entity_prefix = match.group(2)
    entity_number = int(match.group(3))
    sub_number_str = match.group(4)

    if entity_prefix not in factory.all_prefixes:
        return ValidationResult(
            is_valid=False,
            error_message=(
                f"Invalid entity prefix in cross-reference: '{entity_prefix}'"
            ),
        )

    sub_number: int | None = int(sub_number_str) if sub_number_str is not None else None

    return ValidationResult(
        is_valid=True,
        parsed_components={
            "spec_id": spec_id,
            "entity_prefix": entity_prefix,
            "entity_number": entity_number,
            "sub_number": sub_number,
        },
    )


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_cross_reference(ref: str, config: SpecConfiguration) -> CrossReference:
    """Parse a cross-reference string into a CrossReference object.

    Args:
        ref: The cross-reference string to parse.
        config: The specification configuration.

    Returns:
        CrossReference object with parsed components.

    Raises:
        ValueError: If the cross-reference is invalid.
    """
    result = validate_cross_reference(ref, config)
    if not result.is_valid:
        raise ValueError(result.error_message)

    components = result.parsed_components
    if components is None:
        msg = "Validation succeeded but no components returned"
        raise ValueError(msg)

    # Type narrowing: we know these are the correct types from validation
    spec_id = str(components["spec_id"])
    entity_prefix = str(components["entity_prefix"])
    entity_number_val = components["entity_number"]
    entity_number = int(entity_number_val) if entity_number_val is not None else 0
    sub_number_raw = components["sub_number"]
    sub_number: int | None = int(sub_number_raw) if sub_number_raw is not None else None

    return CrossReference(
        spec_id=spec_id,
        entity_prefix=entity_prefix,
        entity_number=entity_number,
        sub_number=sub_number,
    )


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "CrossReference",
    "ParsedID",
    "ValidationResult",
    "next_artifact_id",
    "next_requirement_id",
    "next_spec_id",
    "next_sub_requirement_id",
    "next_test_id",
    "parse_cross_reference",
    "validate_artifact_id",
    "validate_cross_reference",
    "validate_requirement_id",
    "validate_spec_id",
    "validate_test_id",
]
