"""Exit codes and error handling for spec commands.

General exit codes:
    0 - Success
    1 - Entity not found (spec, requirement, test, artifact)
    2 - Validation error (invalid data, duplicate ID, circular dependency)
    3 - Operation cancelled by user
    4 - File system error (read, write, parse)
    5 - Internal error (unexpected exception)
"""

EXIT_SUCCESS: int = 0
"""Command completed successfully."""

EXIT_NOT_FOUND: int = 1
"""Entity not found (spec, requirement, test, or artifact)."""

EXIT_VALIDATION_ERROR: int = 2
"""Validation error (invalid data, duplicate ID, circular dependency)."""

EXIT_CANCELLED: int = 3
"""Operation cancelled by user."""

EXIT_IO_ERROR: int = 4
"""File system error (read, write, parse)."""

EXIT_INTERNAL_ERROR: int = 5
"""Internal error (unexpected exception)."""


def exit_code_for_exception(exc: BaseException) -> int:
    """Map exception to appropriate exit code.

    Args:
        exc: The exception to map.

    Returns:
        Exit code corresponding to the exception type.
    """
    from oaps.exceptions import (
        CircularDependencyError,
        DuplicateIdError,
        OapsRepositoryNotInitializedError,
        RequirementNotFoundError,
        SpecArtifactNotFoundError,
        SpecIOError,
        SpecNotFoundError,
        SpecParseError,
        SpecValidationError,
        TestNotFoundError,
    )

    # Not found errors -> EXIT_NOT_FOUND (1)
    if isinstance(
        exc,
        (
            SpecNotFoundError,
            RequirementNotFoundError,
            TestNotFoundError,
            SpecArtifactNotFoundError,
        ),
    ):
        return EXIT_NOT_FOUND

    # Validation errors -> EXIT_VALIDATION_ERROR (2)
    if isinstance(
        exc,
        (SpecValidationError, DuplicateIdError, CircularDependencyError, ValueError),
    ):
        return EXIT_VALIDATION_ERROR

    # User cancellation -> EXIT_CANCELLED (3)
    if isinstance(exc, KeyboardInterrupt):
        return EXIT_CANCELLED

    # I/O errors -> EXIT_IO_ERROR (4)
    if isinstance(
        exc, (SpecIOError, SpecParseError, OapsRepositoryNotInitializedError, OSError)
    ):
        return EXIT_IO_ERROR

    # Everything else -> EXIT_INTERNAL_ERROR (5)
    return EXIT_INTERNAL_ERROR
