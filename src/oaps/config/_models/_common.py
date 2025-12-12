"""Common configuration types.

This module defines shared types used across configuration models,
including enums and metadata classes.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class LogLevel(StrEnum):
    """Log level threshold values.

    Values are ordered from most verbose (debug) to least verbose (error).
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogFormat(StrEnum):
    """Log output format values."""

    JSON = "json"
    TEXT = "text"


class ConfigSourceName(StrEnum):
    """Configuration source names in precedence order.

    Values are ordered from highest precedence (CLI) to lowest (DEFAULT).
    Higher-precedence sources override lower-precedence sources when merging.
    """

    CLI = "cli"
    ENV = "env"
    WORKTREE = "worktree"
    LOCAL = "local"
    PROJECT = "project"
    USER = "user"
    DEFAULT = "default"


@dataclass(frozen=True, slots=True)
class ConfigSource:
    """Represents a configuration source.

    Attributes:
        name: The source type identifier.
        path: Path to the config file, or None for non-file sources (CLI, ENV, DEFAULT).
        exists: Whether the source exists (file exists, or values are present).
        values: Configuration values from this source.
    """

    name: ConfigSourceName
    path: Path | None
    exists: bool
    values: dict[str, Any]  # pyright: ignore[reportExplicitAny]
