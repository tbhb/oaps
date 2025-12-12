"""Base class for scoped state entities."""

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from oaps.utils import StateStore, StateStoreValue


class ScopedStateEntity(BaseModel):
    """Base class for entities with scoped state storage.

    Provides common state management methods for Session and Project.
    Subclasses must define _default_author property.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    store: StateStore

    @property
    def _default_author(self) -> str:
        """Return the default author for state changes."""
        raise NotImplementedError

    def get(self, key: str) -> StateStoreValue:
        """Get value for key, returning None if not found."""
        try:
            return self.store[key]
        except KeyError:
            return None

    def set(self, key: str, value: StateStoreValue) -> None:
        """Set a value with the default author."""
        self.store.set(key, value, author=self._default_author)

    def increment(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter, initializing to 0 if not exists.

        If the existing value is not numeric, treats it as 0.

        Args:
            key: The key to increment.
            amount: Amount to add (can be negative for decrement).

        Returns:
            The new value after incrementing.
        """
        return self.store.atomic_increment(key, amount, author=self._default_author)

    def set_if_absent(self, key: str, value: StateStoreValue) -> bool:
        """Set value only if key doesn't exist. Returns True if set."""
        if key not in self.store:
            self.set(key, value)
            return True
        return False

    def set_timestamp(self, key: str) -> str:
        """Set key to current UTC timestamp. Returns the timestamp."""
        import pendulum  # noqa: PLC0415

        ts: str = pendulum.now("UTC").to_iso8601_string()
        self.set(key, ts)
        return ts

    def set_timestamp_if_absent(self, key: str) -> str | None:
        """Set key to current UTC timestamp only if key doesn't exist.

        Returns the timestamp if set, None if key already existed.
        """
        if key not in self.store:
            return self.set_timestamp(key)
        return None
