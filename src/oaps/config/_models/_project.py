"""Project configuration model.

This module provides the ProjectConfig Pydantic model for project settings.
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class ProjectConfig(BaseModel):
    """Project configuration section.

    Attributes:
        name: Project name.
        version: Project version.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    name: str = ""
    version: str = ""
