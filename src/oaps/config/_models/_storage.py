"""Storage configuration model.

This module provides the StorageConfiguration Pydantic model for storage settings.
"""

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class StorageConfiguration(BaseModel):
    """OAPS storage configuration.

    Attributes:
        log_level: Log level for state store operation logging.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    log_level: Literal["error", "warning", "info", "debug"] = Field(
        default="info",
        description="Log level for state store operation logging.",
    )
