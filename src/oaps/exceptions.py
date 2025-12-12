"""OAPS exceptions."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class BlockHook(Exception):  # noqa: N818
    """Exception to block hook execution with a message.

    Attributes:
        output_json: Optional JSON string for hook-specific output to include
            in the response to Claude Code.
    """

    def __init__(self, message: str = "", *, output_json: str | None = None) -> None:
        """Initialize BlockHook with message and optional output JSON.

        Args:
            message: Human-readable message explaining the block reason.
            output_json: Optional JSON string for hook-specific output.
        """
        super().__init__(message)
        self.output_json: str | None = output_json


class OAPSError(Exception):
    """Base exception for OAPS errors."""


class HookError(OAPSError):
    """Base exception for hook errors."""


class ExpressionError(HookError):
    """Raised when an expression is invalid or cannot be evaluated."""

    def __init__(
        self,
        message: str,
        *,
        expression: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize with error message and expression context."""
        super().__init__(message)
        self.expression: str = expression
        self.cause: Exception | None = cause


class WorktreeError(OAPSError):
    """Base exception for worktree errors."""


class WorktreeNotFoundError(WorktreeError):
    """Worktree not found at the specified path."""


class WorktreeLockedError(WorktreeError):
    """Operation blocked because worktree is locked."""


class WorktreeDirtyError(WorktreeError):
    """Uncommitted changes prevent removal of worktree."""


class ConfigError(OAPSError):
    """Base exception for configuration errors."""


class ConfigLoadError(ConfigError):
    """Raised when configuration cannot be loaded or parsed."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """Initialize with error message and optional location context."""
        super().__init__(message)
        self.path: Path | None = path
        self.line: int | None = line
        self.column: int | None = column


class ConfigValidationError(ConfigError):
    """Raised when configuration fails validation."""

    def __init__(
        self,
        message: str,
        *,
        key: str,
        value: Any,  # pyright: ignore[reportAny,reportExplicitAny]
        expected: str,
        source: str | None = None,
    ) -> None:
        """Initialize with error message and validation context."""
        super().__init__(message)
        self.key: str = key
        self.value: Any = value  # pyright: ignore[reportExplicitAny]
        self.expected: str = expected
        self.source: str | None = source


# =============================================================================
# Artifact Exceptions
# =============================================================================


class ArtifactError(OAPSError):
    """Base exception for artifact operations."""


class ArtifactNotFoundError(ArtifactError, KeyError):
    """Raised when an artifact cannot be found.

    Attributes:
        artifact_id: The ID of the artifact that was not found.
    """

    def __init__(self, message: str, *, artifact_id: str | None = None) -> None:
        """Initialize with error message and artifact context.

        Args:
            message: Human-readable error message.
            artifact_id: The ID of the artifact that was not found.
        """
        super().__init__(message)
        self.artifact_id: str | None = artifact_id


class ArtifactValidationError(ArtifactError, ValueError):
    """Raised when artifact validation fails.

    Attributes:
        artifact_id: The ID of the artifact that failed validation.
        field: The field that failed validation (if applicable).
    """

    def __init__(
        self,
        message: str,
        *,
        artifact_id: str | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize with error message and validation context.

        Args:
            message: Human-readable error message.
            artifact_id: The ID of the artifact that failed validation.
            field: The field that failed validation.
        """
        super().__init__(message)
        self.artifact_id: str | None = artifact_id
        self.field: str | None = field


class TypeNotRegisteredError(ArtifactError, ValueError):
    """Raised when an artifact type is not registered.

    Attributes:
        prefix: The type prefix that was not found.
    """

    def __init__(self, message: str, *, prefix: str | None = None) -> None:
        """Initialize with error message and type context.

        Args:
            message: Human-readable error message.
            prefix: The type prefix that was not found.
        """
        super().__init__(message)
        self.prefix: str | None = prefix


class DuplicateArtifactError(ArtifactError, ValueError):
    """Raised when an artifact ID already exists.

    Attributes:
        artifact_id: The ID that already exists.
    """

    def __init__(self, message: str, *, artifact_id: str | None = None) -> None:
        """Initialize with error message and artifact context.

        Args:
            message: Human-readable error message.
            artifact_id: The ID that already exists.
        """
        super().__init__(message)
        self.artifact_id: str | None = artifact_id


# =============================================================================
# Specification Exceptions
# =============================================================================


class SpecError(OAPSError):
    """Base exception for specification system errors."""


class SpecIOError(SpecError):
    """Raised when a specification file cannot be read or written.

    Attributes:
        path: Path to the file that caused the error.
        operation: The operation that failed ("read", "write", "append").
        cause: The underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path,
        operation: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize with error message and I/O context.

        Args:
            message: Human-readable error message.
            path: Path to the file that caused the error.
            operation: The operation that failed ("read", "write", "append").
            cause: The underlying exception that caused this error.
        """
        super().__init__(message)
        self.path: Path = path
        self.operation: str = operation
        self.cause: Exception | None = cause


class SpecParseError(SpecError):
    """Raised when specification file content cannot be parsed.

    Attributes:
        path: Path to the file that caused the error.
        line: Line number where the parse error occurred.
        content_type: The content type that failed to parse.
        cause: The underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path,
        line: int | None = None,
        content_type: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize with error message and parse context.

        Args:
            message: Human-readable error message.
            path: Path to the file that caused the error.
            line: Line number where the parse error occurred.
            content_type: The content type that failed to parse.
            cause: The underlying exception that caused this error.
        """
        super().__init__(message)
        self.path: Path = path
        self.line: int | None = line
        self.content_type: str = content_type
        self.cause: Exception | None = cause


class SpecNotFoundError(SpecError, KeyError):
    """Raised when a specification cannot be found.

    Attributes:
        spec_id: The ID of the specification that was not found.
    """

    def __init__(self, message: str, *, spec_id: str | None = None) -> None:
        """Initialize with error message and spec context.

        Args:
            message: Human-readable error message.
            spec_id: The ID of the specification that was not found.
        """
        super().__init__(message)
        self.spec_id: str | None = spec_id


class RequirementNotFoundError(SpecError, KeyError):
    """Raised when a requirement cannot be found.

    Attributes:
        requirement_id: The ID of the requirement that was not found.
        spec_id: The ID of the specification containing the requirement.
    """

    def __init__(
        self,
        message: str,
        *,
        requirement_id: str | None = None,
        spec_id: str | None = None,
    ) -> None:
        """Initialize with error message and requirement context.

        Args:
            message: Human-readable error message.
            requirement_id: The ID of the requirement that was not found.
            spec_id: The ID of the specification containing the requirement.
        """
        super().__init__(message)
        self.requirement_id: str | None = requirement_id
        self.spec_id: str | None = spec_id


class TestNotFoundError(SpecError, KeyError):
    """Raised when a test cannot be found.

    Attributes:
        test_id: The ID of the test that was not found.
        spec_id: The ID of the specification containing the test.
    """

    def __init__(
        self,
        message: str,
        *,
        test_id: str | None = None,
        spec_id: str | None = None,
    ) -> None:
        """Initialize with error message and test context.

        Args:
            message: Human-readable error message.
            test_id: The ID of the test that was not found.
            spec_id: The ID of the specification containing the test.
        """
        super().__init__(message)
        self.test_id: str | None = test_id
        self.spec_id: str | None = spec_id


class SpecArtifactNotFoundError(SpecError, KeyError):
    """Raised when a specification artifact cannot be found.

    Attributes:
        artifact_id: The ID of the artifact that was not found.
        spec_id: The ID of the specification containing the artifact.
    """

    def __init__(
        self,
        message: str,
        *,
        artifact_id: str | None = None,
        spec_id: str | None = None,
    ) -> None:
        """Initialize with error message and artifact context.

        Args:
            message: Human-readable error message.
            artifact_id: The ID of the artifact that was not found.
            spec_id: The ID of the specification containing the artifact.
        """
        super().__init__(message)
        self.artifact_id: str | None = artifact_id
        self.spec_id: str | None = spec_id


class SpecValidationError(SpecError, ValueError):
    """Raised when specification validation fails.

    Attributes:
        spec_id: The ID of the specification that failed validation.
        field: The field that failed validation.
        value: The invalid value.
        expected: Description of what was expected.
    """

    def __init__(
        self,
        message: str,
        *,
        spec_id: str | None = None,
        field: str | None = None,
        value: Any = None,  # pyright: ignore[reportAny,reportExplicitAny]
        expected: str | None = None,
    ) -> None:
        """Initialize with error message and validation context.

        Args:
            message: Human-readable error message.
            spec_id: The ID of the specification that failed validation.
            field: The field that failed validation.
            value: The invalid value.
            expected: Description of what was expected.
        """
        super().__init__(message)
        self.spec_id: str | None = spec_id
        self.field: str | None = field
        self.value: Any = value  # pyright: ignore[reportExplicitAny]
        self.expected: str | None = expected


class DuplicateIdError(SpecError, ValueError):
    """Raised when a duplicate ID is detected.

    Attributes:
        entity_id: The ID that already exists.
        entity_type: The type of entity (e.g., 'spec', 'requirement', 'test').
        spec_id: The ID of the specification where the duplicate was found.
    """

    def __init__(
        self,
        message: str,
        *,
        entity_id: str,
        entity_type: str | None = None,
        spec_id: str | None = None,
    ) -> None:
        """Initialize with error message and duplicate context.

        Args:
            message: Human-readable error message.
            entity_id: The ID that already exists.
            entity_type: The type of entity (e.g., 'spec', 'requirement', 'test').
            spec_id: The ID of the specification where the duplicate was found.
        """
        super().__init__(message)
        self.entity_id: str = entity_id
        self.entity_type: str | None = entity_type
        self.spec_id: str | None = spec_id


class CircularDependencyError(SpecError, ValueError):
    """Raised when a circular dependency is detected.

    Attributes:
        cycle: List of entity IDs forming the circular dependency.
        entity_type: The type of entities involved in the cycle.
    """

    def __init__(
        self,
        message: str,
        *,
        cycle: list[str] | None = None,
        entity_type: str | None = None,
    ) -> None:
        """Initialize with error message and cycle context.

        Args:
            message: Human-readable error message.
            cycle: List of entity IDs forming the circular dependency.
            entity_type: The type of entities involved in the cycle.
        """
        super().__init__(message)
        self.cycle: list[str] | None = cycle
        self.entity_type: str | None = entity_type


# =============================================================================
# Idea Exceptions
# =============================================================================


class IdeaError(OAPSError):
    """Base exception for idea system errors."""


class IdeaNotFoundError(IdeaError, KeyError):
    """Raised when an idea cannot be found.

    Attributes:
        idea_id: The ID of the idea that was not found.
    """

    def __init__(self, message: str, *, idea_id: str | None = None) -> None:
        """Initialize with error message and idea context.

        Args:
            message: Human-readable error message.
            idea_id: The ID of the idea that was not found.
        """
        super().__init__(message)
        self.idea_id: str | None = idea_id


class IdeaValidationError(IdeaError, ValueError):
    """Raised when idea validation fails.

    Attributes:
        idea_id: The ID of the idea that failed validation.
        field: The field that failed validation.
        value: The invalid value.
        expected: Description of what was expected.
    """

    def __init__(
        self,
        message: str,
        *,
        idea_id: str | None = None,
        field: str | None = None,
        value: Any = None,  # pyright: ignore[reportAny,reportExplicitAny]
        expected: str | None = None,
    ) -> None:
        """Initialize with error message and validation context.

        Args:
            message: Human-readable error message.
            idea_id: The ID of the idea that failed validation.
            field: The field that failed validation.
            value: The invalid value.
            expected: Description of what was expected.
        """
        super().__init__(message)
        self.idea_id: str | None = idea_id
        self.field: str | None = field
        self.value: Any = value  # pyright: ignore[reportExplicitAny]
        self.expected: str | None = expected


# =============================================================================
# OapsRepository Exceptions
# =============================================================================


class OapsRepositoryError(OAPSError):
    """Base exception for OapsRepository errors."""


class OapsRepositoryNotInitializedError(OapsRepositoryError):
    """Raised when .oaps/.git is not found or invalid.

    Attributes:
        path: The directory that was searched for .oaps/.git.
    """

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        """Initialize with error message and path context.

        Args:
            message: Human-readable error message.
            path: The directory that was searched for .oaps/.git.
        """
        super().__init__(message)
        self.path: Path | None = path


class OapsRepositoryReadOnlyError(OapsRepositoryError):
    """Raised when repository is not writable.

    Attributes:
        path: The path that is not writable.
    """

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        """Initialize with error message and path context.

        Args:
            message: Human-readable error message.
            path: The path that is not writable.
        """
        super().__init__(message)
        self.path: Path | None = path


class OapsRepositoryConflictError(OapsRepositoryError):
    """Raised when a commit conflict is detected.

    Attributes:
        path: The path where the conflict occurred.
        details: Additional details about the conflict.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        details: str | None = None,
    ) -> None:
        """Initialize with error message and conflict context.

        Args:
            message: Human-readable error message.
            path: The path where the conflict occurred.
            details: Additional details about the conflict.
        """
        super().__init__(message)
        self.path: Path | None = path
        self.details: str | None = details


class OapsRepositoryPathViolationError(OapsRepositoryError):
    """Raised when attempting to operate on files outside .oaps/.

    Attributes:
        path: The path that violated the constraint.
        oaps_root: The .oaps/ root directory.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        oaps_root: Path | None = None,
    ) -> None:
        """Initialize with error message and path violation context.

        Args:
            message: Human-readable error message.
            path: The path that violated the constraint.
            oaps_root: The .oaps/ root directory.
        """
        super().__init__(message)
        self.path: Path | None = path
        self.oaps_root: Path | None = oaps_root


# =============================================================================
# ProjectRepository Exceptions
# =============================================================================


class ProjectRepositoryError(OAPSError):
    """Base exception for ProjectRepository errors."""


class ProjectRepositoryNotInitializedError(ProjectRepositoryError):
    """Raised when project .git is not found.

    Attributes:
        path: The directory that was searched for .git.
    """

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        """Initialize with error message and path context.

        Args:
            message: Human-readable error message.
            path: The directory that was searched for .git.
        """
        super().__init__(message)
        self.path: Path | None = path


# =============================================================================
# Supervisor Exceptions
# =============================================================================


class SupervisorError(OAPSError):
    """Base exception for supervisor errors."""


class ServiceNotFoundError(SupervisorError, KeyError):
    """Raised when a service cannot be found by name.

    Attributes:
        service_name: The name of the service that was not found.
    """

    def __init__(self, message: str, *, service_name: str | None = None) -> None:
        """Initialize with error message and service context.

        Args:
            message: Human-readable error message.
            service_name: The name of the service that was not found.
        """
        super().__init__(message)
        self.service_name: str | None = service_name


class ServiceStartError(SupervisorError):
    """Raised when a service fails to start.

    Attributes:
        service_name: The name of the service that failed to start.
        cause: The underlying exception that caused the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize with error message and service context.

        Args:
            message: Human-readable error message.
            service_name: The name of the service that failed to start.
            cause: The underlying exception that caused the failure.
        """
        super().__init__(message)
        self.service_name: str | None = service_name
        self.cause: Exception | None = cause


class ServiceStopError(SupervisorError):
    """Raised when a service fails to stop gracefully.

    Attributes:
        service_name: The name of the service that failed to stop.
        cause: The underlying exception that caused the failure.
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize with error message and service context.

        Args:
            message: Human-readable error message.
            service_name: The name of the service that failed to stop.
            cause: The underlying exception that caused the failure.
        """
        super().__init__(message)
        self.service_name: str | None = service_name
        self.cause: Exception | None = cause
