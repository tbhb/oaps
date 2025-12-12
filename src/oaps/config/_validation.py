# pyright: reportAny=false, reportExplicitAny=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false
"""Configuration validation using Pydantic schemas.

This module provides validation for OAPS configuration dictionaries.
It uses the frozen Pydantic models from _models/ and provides strict
variants for validation that rejects unknown keys.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from oaps.config._models._hooks import HooksConfiguration
from oaps.config._models._ideas import IdeasConfiguration
from oaps.config._models._logging import LoggingConfig
from oaps.config._models._project import ProjectConfig
from oaps.config._models._spec import SpecConfiguration
from oaps.config._models._storage import StorageConfiguration
from oaps.exceptions import ConfigValidationError

if TYPE_CHECKING:
    from pydantic_core import ErrorDetails

    from oaps.config._models._common import ConfigSource, ConfigSourceName


# -----------------------------------------------------------------------------
# Validation Issue
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Represents a configuration validation issue.

    Attributes:
        key: Dotted path to the configuration key (e.g., "logging.level").
        message: Human-readable description of the issue.
        expected: Description of expected value or type, if available.
        actual: The actual value that caused the issue.
        source: Name of the ConfigSource where the issue was found, or None.
        severity: Whether this is an error or warning.
    """

    key: str
    message: str
    expected: str | None
    actual: Any
    source: str | None
    severity: Literal["error", "warning"]


# -----------------------------------------------------------------------------
# Pydantic Schemas (Lenient Mode - ignores unknown keys)
# The base models from _models/ already have extra="ignore", so we use them
# directly in ConfigSchema.
# -----------------------------------------------------------------------------


class ConfigSchema(BaseModel):
    """Pydantic schema for root configuration (lenient mode)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    hooks: HooksConfiguration = HooksConfiguration()
    ideas: IdeasConfiguration = IdeasConfiguration()
    logging: LoggingConfig = LoggingConfig()
    project: ProjectConfig = ProjectConfig()
    spec: SpecConfiguration = SpecConfiguration()
    storage: StorageConfiguration = StorageConfiguration()


# -----------------------------------------------------------------------------
# Pydantic Schemas (Strict Mode - rejects unknown keys)
# These inherit from the base models and override extra="forbid".
# -----------------------------------------------------------------------------


class LoggingConfigStrict(LoggingConfig):
    """Pydantic schema for logging configuration section (strict mode)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class ProjectConfigStrict(ProjectConfig):
    """Pydantic schema for project configuration section (strict mode)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class IdeasConfigurationStrict(IdeasConfiguration):
    """Pydantic schema for ideas configuration section (strict mode)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class ConfigSchemaStrict(BaseModel):
    """Pydantic schema for root configuration (strict mode)."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    hooks: HooksConfiguration = HooksConfiguration()
    ideas: IdeasConfigurationStrict = IdeasConfigurationStrict()
    logging: LoggingConfigStrict = LoggingConfigStrict()
    project: ProjectConfigStrict = ProjectConfigStrict()
    spec: SpecConfiguration = SpecConfiguration()
    storage: StorageConfiguration = StorageConfiguration()


# -----------------------------------------------------------------------------
# Validation Functions
# -----------------------------------------------------------------------------


def _pydantic_error_to_issue(
    error: ErrorDetails,
    source: str | None,
) -> ValidationIssue:
    """Convert a Pydantic error dict to a ValidationIssue.

    Args:
        error: A single error dict from ValidationError.errors().
        source: The ConfigSourceName value, or None for merged config.

    Returns:
        A ValidationIssue representing the validation error.
    """
    # Extract the key path from loc tuple
    loc = error.get("loc", ())
    key = ".".join(str(part) for part in loc)

    # Get the error message
    message = str(error.get("msg", "Validation error"))

    # Extract expected value from ctx if available
    ctx = error.get("ctx")
    expected: str | None = None
    if ctx is not None:
        if "expected" in ctx:
            expected = str(ctx["expected"])
        elif "pattern" in ctx:
            expected = f"pattern: {ctx['pattern']}"

    # Get the actual input value
    actual = error.get("input")

    return ValidationIssue(
        key=key,
        message=message,
        expected=expected,
        actual=actual,
        source=source,
        severity="error",
    )


def validate_config(
    config: dict[str, Any],
    *,
    strict: bool = False,
) -> list[ValidationIssue]:
    """Validate a merged configuration dictionary.

    Args:
        config: The merged configuration dictionary to validate.
        strict: If True, unknown keys are errors. If False, they are ignored.

    Returns:
        List of ValidationIssue objects. Empty list indicates valid config.
    """
    schema_class = ConfigSchemaStrict if strict else ConfigSchema

    try:
        _ = schema_class.model_validate(config)
    except ValidationError as e:
        return [_pydantic_error_to_issue(err, source=None) for err in e.errors()]
    else:
        return []


def validate_source(source: ConfigSource) -> list[ValidationIssue]:
    """Validate a single ConfigSource's values.

    Args:
        source: The ConfigSource to validate.

    Returns:
        List of ValidationIssue objects tagged with source.name.
        Empty list if source is empty, doesn't exist, or is valid.
    """
    if not source.exists or not source.values:
        return []

    source_name: ConfigSourceName = source.name

    try:
        # Use lenient schema for individual sources
        _ = ConfigSchema.model_validate(source.values)
    except ValidationError as e:
        return [
            _pydantic_error_to_issue(err, source=source_name.value)
            for err in e.errors()
        ]
    else:
        return []


def raise_if_validation_errors(
    issues: list[ValidationIssue],
    source: str | None = None,
) -> None:
    """Raise ConfigValidationError if any validation errors exist.

    This is a convenience function that checks a list of validation issues
    and raises an exception for the first error found.

    Args:
        issues: List of ValidationIssue objects to check.
        source: Optional source string to use in the exception.
            If not provided, uses the source from the first error.

    Raises:
        ConfigValidationError: If any issues have severity="error".
    """
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        issue = errors[0]
        msg = f"Invalid configuration value for '{issue.key}'"
        raise ConfigValidationError(
            msg,
            key=issue.key,
            value=issue.actual,
            expected=issue.expected or issue.message,
            source=source or issue.source,
        )


def get_config_schema(*, strict: bool = False) -> dict[str, Any]:
    """Get the JSON Schema for OAPS configuration.

    Returns a JSON Schema (Draft 2020-12) dictionary describing the
    structure and constraints of OAPS configuration files.

    Args:
        strict: If True, returns schema that rejects unknown keys.
            If False (default), returns schema that ignores unknown keys.

    Returns:
        JSON Schema dictionary for OAPS configuration.

    Examples:
        >>> schema = get_config_schema()
        >>> schema["title"]
        'ConfigSchema'
        >>> "logging" in schema["properties"]
        True
    """
    schema_class = ConfigSchemaStrict if strict else ConfigSchema
    return schema_class.model_json_schema()
