from typing import ClassVar, override

from pydantic import ConfigDict

from oaps.state import ScopedStateEntity
from oaps.utils import StateStore  # noqa: TC001


class Project(ScopedStateEntity):
    """Represents an OAPS project with persistent state storage."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    store: StateStore

    @property
    @override
    def _default_author(self) -> str:
        """Return the default author for project state changes."""
        return "oaps.project"
