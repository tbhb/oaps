"""Logging utilities for OAPS.

This module provides standalone structlog logger factories that write
JSON-formatted or text-formatted logs to OAPS log files. Each logger is
self-contained and does not modify global structlog configuration.
"""

import logging
from logging.handlers import RotatingFileHandler
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from uuid import UUID  # noqa: TC003 - Used at runtime in type annotation

import structlog

from ._paths import (
    get_oaps_cli_log_file,
    get_oaps_hooks_log_file,
    get_oaps_session_log_file,
)

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

LogFormatType = Literal["json", "text"]


def _get_log_level() -> int:
    """Get the log level from environment variables.

    Checks OAPS_DEBUG first (sets DEBUG if present), then OAPS_LOG_LEVEL.
    Defaults to INFO if neither is set.

    Returns:
        The logging level as an integer.
    """
    if getenv("OAPS_DEBUG", None):
        return logging.DEBUG

    log_levels = logging.getLevelNamesMapping()
    return log_levels.get(getenv("OAPS_LOG_LEVEL", "info").upper(), logging.INFO)


def _log_level_from_string(level: str, *, respect_env: bool = False) -> int:
    """Convert a log level string to a logging level integer.

    Args:
        level: Log level string (debug, info, warning, error).
        respect_env: If True, OAPS_DEBUG overrides to DEBUG level.

    Returns:
        The logging level as an integer.
    """
    if respect_env and getenv("OAPS_DEBUG", None):
        return logging.DEBUG

    log_levels = logging.getLevelNamesMapping()
    return log_levels.get(level.upper(), logging.INFO)


def _create_logger(
    log_file_path: str,
    *,
    log_level: int | None = None,
    log_format: LogFormatType = "json",
    max_bytes: int | None = None,
    backup_count: int | None = None,
) -> "FilteringBoundLogger":  # noqa: UP037
    """Create a standalone structlog logger writing to the specified file.

    Args:
        log_file_path: Path to the log file (will be opened in append mode).
        log_level: Override log level (uses env vars if not specified).
        log_format: Output format, either "json" or "text".
        max_bytes: Maximum size in bytes before rotation. Must be set with
            backup_count for rotation to be enabled.
        backup_count: Number of rotated log files to keep. Must be set with
            max_bytes for rotation to be enabled.

    Returns:
        A configured FilteringBoundLogger instance.
    """
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    effective_level = log_level if log_level is not None else _get_log_level()

    # Create a standalone logger factory for this specific file
    # Use stdlib logger with RotatingFileHandler when both max_bytes and backup_count
    # are provided, otherwise use direct file writing
    stdlib_logger: logging.Logger | None = None
    if max_bytes is not None and backup_count is not None:
        # Use stdlib logging with RotatingFileHandler for proper rotation support
        stdlib_logger = logging.getLogger(f"oaps.{log_path.stem}.{id(log_path)}")
        stdlib_logger.handlers.clear()
        stdlib_logger.propagate = False
        stdlib_logger.setLevel(effective_level)

        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        handler.setLevel(effective_level)
        # Use a simple formatter - structlog will handle the actual formatting
        handler.setFormatter(logging.Formatter("%(message)s"))
        stdlib_logger.addHandler(handler)

        logger_factory = structlog.stdlib.LoggerFactory()
    else:
        logger_factory = structlog.WriteLoggerFactory(file=log_path.open("a"))

    # Create processors based on format
    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if log_format == "json":
        # Add dict_tracebacks for structured exception logging in JSON
        processors.append(structlog.processors.dict_tracebacks)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Text format: "timestamp [level] event key=value ..."
        processors.append(structlog.dev.ConsoleRenderer(colors=False))

    # Create a bound logger with the configured processors
    wrapper_class = structlog.make_filtering_bound_logger(effective_level)

    # Use wrap_logger for standalone logger creation (doesn't affect global config)
    # For rotating logs, use the stdlib logger; otherwise use the WriteLoggerFactory
    raw_logger = stdlib_logger if stdlib_logger is not None else logger_factory()

    return cast(
        "FilteringBoundLogger",
        structlog.wrap_logger(
            raw_logger,
            processors=processors,
            wrapper_class=wrapper_class,
            context_class=dict,
        ),
    )


def create_hooks_logger(
    level: str | None = None,
    *,
    max_bytes: int | None = None,
    backup_count: int | None = None,
) -> "FilteringBoundLogger":  # noqa: UP037
    """Create a logger for OAPS hooks.

    Creates a standalone structlog logger that writes JSON-formatted logs
    to the hooks log file at .oaps/logs/hooks.log.

    The log level is determined by (in order of precedence):
    1. OAPS_DEBUG environment variable (if set, enables DEBUG level)
    2. The `level` parameter (if provided)
    3. OAPS_LOG_LEVEL environment variable
    4. Default: INFO

    Args:
        level: Optional log level string (debug, info, warning, error).
            If provided, overrides OAPS_LOG_LEVEL but not OAPS_DEBUG.
        max_bytes: Maximum size in bytes before rotation. Must be set with
            backup_count for rotation to be enabled.
        backup_count: Number of rotated log files to keep. Must be set with
            max_bytes for rotation to be enabled.

    Returns:
        A FilteringBoundLogger instance configured for hooks logging.
    """
    hooks_log_file = get_oaps_hooks_log_file()

    # Determine effective log level
    effective_level: int | None = None
    if level is not None:
        effective_level = _log_level_from_string(level, respect_env=True)

    return _create_logger(
        str(hooks_log_file),
        log_level=effective_level,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )


def create_session_logger(
    session_id: str | UUID,
    *,
    level: str | None = None,
) -> "FilteringBoundLogger":  # noqa: UP037
    """Create a logger for a specific Claude Code session.

    Creates a standalone structlog logger that writes JSON-formatted logs
    to the session log file at .oaps/logs/sessions/<session_id>.log.

    The log level is determined by (in order of precedence):
    1. OAPS_DEBUG environment variable (if set, enables DEBUG level)
    2. The `level` parameter (if provided)
    3. OAPS_LOG_LEVEL environment variable
    4. Default: INFO

    Args:
        session_id: The Claude Code session ID.
        level: Optional log level string (debug, info, warning, error).
            If provided, overrides OAPS_LOG_LEVEL but not OAPS_DEBUG.

    Returns:
        A FilteringBoundLogger instance configured for session logging.
    """
    session_log_file = get_oaps_session_log_file(session_id)

    # Determine effective log level
    effective_level: int | None = None
    if level is not None:
        effective_level = _log_level_from_string(level, respect_env=True)

    return _create_logger(str(session_log_file), log_level=effective_level)


def create_cli_logger(
    *,
    level: str = "info",
    log_format: LogFormatType = "json",
    log_file: str = "",
    command: str = "",
) -> "FilteringBoundLogger":  # noqa: UP037
    """Create a logger for CLI commands.

    Creates a standalone structlog logger that writes structured logs
    to either a specified file or the default CLI log file at .oaps/logs/cli.log.

    The logger automatically binds the command name to all log entries.

    The log level can be overridden by environment variables:
    - OAPS_DEBUG: If set, enables DEBUG level logging regardless of config

    Args:
        level: Log level threshold (debug, info, warning, error).
        log_format: Output format, either "json" or "text".
        log_file: Path to log file (uses default .oaps/logs/cli.log if empty).
        command: Name of the CLI command for context (bound to all entries).

    Returns:
        A FilteringBoundLogger instance configured for CLI logging.
    """
    effective_file = log_file if log_file else str(get_oaps_cli_log_file())
    effective_level = _log_level_from_string(level, respect_env=True)

    logger = _create_logger(
        effective_file,
        log_level=effective_level,
        log_format=log_format,
    )

    # Bind command name to all log entries if provided
    if command:
        return logger.bind(command=command)
    return logger
