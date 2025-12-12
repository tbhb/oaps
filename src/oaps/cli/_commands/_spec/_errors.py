"""Exit codes and error handling for spec commands."""

from oaps.cli._commands._shared import ExitCode


def exit_code_for_exception(exc: BaseException) -> ExitCode:
    """Map exception to appropriate exit code.

    Args:
        exc: The exception to map.

    Returns:
        ExitCode corresponding to the exception type.
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

    # Not found errors -> NOT_FOUND (3)
    if isinstance(
        exc,
        (
            SpecNotFoundError,
            RequirementNotFoundError,
            TestNotFoundError,
            SpecArtifactNotFoundError,
        ),
    ):
        return ExitCode.NOT_FOUND

    # Validation errors -> VALIDATION_ERROR (2)
    if isinstance(
        exc,
        (SpecValidationError, DuplicateIdError, CircularDependencyError, ValueError),
    ):
        return ExitCode.VALIDATION_ERROR

    # User cancellation -> NOT_FOUND (3) - legacy mapping
    if isinstance(exc, KeyboardInterrupt):
        return ExitCode.NOT_FOUND

    # I/O errors -> IO_ERROR (4)
    if isinstance(
        exc, (SpecIOError, SpecParseError, OapsRepositoryNotInitializedError, OSError)
    ):
        return ExitCode.IO_ERROR

    # Everything else -> INTERNAL_ERROR (5)
    return ExitCode.INTERNAL_ERROR
