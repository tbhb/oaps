from typing import ClassVar, override

from pydantic import ConfigDict

from oaps.state import ScopedStateEntity
from oaps.utils import StateStore  # noqa: TC001


class Session(ScopedStateEntity):
    """Represents a Claude Code session."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    id: str
    store: StateStore

    @property
    @override
    def _default_author(self) -> str:
        """Return the default author for session state changes."""
        return "oaps.hooks"
