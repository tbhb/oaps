"""Logging configuration model.

This module provides the LoggingConfig Pydantic model for logging settings.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from oaps.config._models._common import LogFormat, LogLevel


class LoggingConfig(BaseModel):
    """Logging configuration section.

    Attributes:
        level: Log level threshold.
        format: Log output format.
        file: Path to log file (empty disables file logging).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.JSON
    file: str = ""
