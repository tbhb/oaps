# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# ruff: noqa: D415, FBT002
"""Commands for session state management."""

from os import getenv
from typing import TYPE_CHECKING, Annotated

from cyclopts import App, Parameter

if TYPE_CHECKING:
    from oaps.utils import SQLiteStateStore, StateEntry, StateStoreValue

app = App(
    name="session", help="Manage session state (key-value store)", help_on_error=True
)


def _get_session_id_from_env() -> str | None:
    """Get session ID from environment variable."""
    return getenv("CLAUDE_SESSION_ID")


def _get_store(session_id: str | None = None) -> SQLiteStateStore:
    """Get or create a state store for the given session ID.

    Args:
        session_id: Optional session ID. Uses CLAUDE_SESSION_ID env var if not provided.

    Returns:
        A SQLiteStateStore instance.

    Raises:
        SystemExit: If no session ID is available.
    """
    from oaps.utils import SQLiteStateStore, get_oaps_state_file

    effective_session_id = session_id or _get_session_id_from_env()
    if not effective_session_id:
        print("Error: No session ID provided and CLAUDE_SESSION_ID not set")
        raise SystemExit(1)

    db_path = get_oaps_state_file()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStateStore(db_path, session_id=effective_session_id)


def _parse_value(value: str) -> StateStoreValue:
    """Parse a string value into the appropriate type.

    Attempts to parse as int first, then float, falling back to string.

    Args:
        value: The string value from CLI input.

    Returns:
        The parsed value as int, float, or the original string.
    """
    # Try int first
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Fall back to string
    return value


def _format_value(value: StateStoreValue) -> str:
    """Format a session store value for display.

    Args:
        value: The value to format.

    Returns:
        A string representation of the value.
    """
    if value is None:
        return "null"
    if isinstance(value, bytes):
        return f"<bytes: {len(value)} bytes>"
    return str(value)


def _format_entry_verbose(entry: StateEntry) -> str:
    """Format a session store entry with full metadata.

    Args:
        entry: The entry to format.

    Returns:
        A formatted string with all metadata.
    """
    lines = [
        f"key: {entry.key}",
        f"value: {_format_value(entry.value)}",
        f"created_at: {entry.created_at}",
        f"created_by: {entry.created_by or 'null'}",
        f"updated_at: {entry.updated_at}",
        f"updated_by: {entry.updated_by or 'null'}",
    ]
    return "\n".join(lines)


@app.command(name="get")
def _get(
    key: str,
    /,
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    verbose: Annotated[bool, Parameter(help="Show full entry metadata")] = False,
) -> None:
    """Get a value from the session store

    Args:
        key: The key to look up
        session_id: Optional session ID override
        verbose: Whether to show full entry metadata
    """
    store = _get_store(session_id)

    if verbose:
        entry = store.get_entry(key)
        if entry is None:
            print(f"Error: Key '{key}' not found")
            raise SystemExit(1)
        print(_format_entry_verbose(entry))
    else:
        if key not in store:
            print(f"Error: Key '{key}' not found")
            raise SystemExit(1)
        print(_format_value(store[key]))


@app.command(name="set")
def _set(
    key: str,
    value: str,
    /,
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
    string: Annotated[
        bool, Parameter(help="Store value as string (skip numeric detection)")
    ] = False,
) -> None:
    """Set a value in the session store

    By default, numeric values are detected and stored as int/float.
    Use --string to force storing as a string.

    Args:
        key: The key to set
        value: The value to store
        session_id: Optional session ID override
        author: Optional author attribution
        string: Force storing as string
    """
    store = _get_store(session_id)
    parsed_value = value if string else _parse_value(value)
    store.set(key, parsed_value, author=author)
    print(f"Set '{key}' = {parsed_value}")


@app.command(name="delete")
def _delete(
    key: str,
    /,
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
) -> None:
    """Delete a key from the session store

    Args:
        key: The key to delete
        session_id: Optional session ID override
    """
    store = _get_store(session_id)
    if store.delete(key):
        print(f"Deleted '{key}'")
    else:
        print(f"Key '{key}' not found")
        raise SystemExit(1)


@app.command(name="clear")
def _clear(
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    force: Annotated[bool, Parameter(help="Skip confirmation prompt")] = False,
) -> None:
    """Clear all entries from the session store

    Args:
        session_id: Optional session ID override
        force: Skip confirmation prompt
    """
    store = _get_store(session_id)
    count = len(store)

    if count == 0:
        print("Session store is already empty")
        return

    if not force:
        print(f"This will delete {count} entries. Use --force to confirm.")
        raise SystemExit(1)

    store.clear()
    print(f"Cleared {count} entries from session store")


@app.command(name="increment")
def _increment(
    key: str,
    /,
    amount: Annotated[int, Parameter(help="Amount to increment by")] = 1,
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
) -> None:
    """Increment a numeric value in the session store

    Creates the key with the increment amount if it doesn't exist.

    Args:
        key: The key to increment
        amount: Amount to increment by (default 1)
        session_id: Optional session ID override
        author: Optional author attribution
    """
    store = _get_store(session_id)

    current_value: int = 0
    if key in store:
        existing = store[key]
        if not isinstance(existing, int):
            type_name = type(existing).__name__
            print(f"Error: Key '{key}' exists but is not an integer (got {type_name})")
            raise SystemExit(1)
        current_value = existing

    new_value = current_value + amount
    store.set(key, new_value, author=author)
    print(f"{key} = {new_value}")


@app.command(name="decrement")
def _decrement(
    key: str,
    /,
    amount: Annotated[int, Parameter(help="Amount to decrement by")] = 1,
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    author: Annotated[str | None, Parameter(help="Author of this change")] = None,
) -> None:
    """Decrement a numeric value in the session store

    Creates the key with the negative decrement amount if it doesn't exist.

    Args:
        key: The key to decrement
        amount: Amount to decrement by (default 1)
        session_id: Optional session ID override
        author: Optional author attribution
    """
    store = _get_store(session_id)

    current_value: int = 0
    if key in store:
        existing = store[key]
        if not isinstance(existing, int):
            type_name = type(existing).__name__
            print(f"Error: Key '{key}' exists but is not an integer (got {type_name})")
            raise SystemExit(1)
        current_value = existing

    new_value = current_value - amount
    store.set(key, new_value, author=author)
    print(f"{key} = {new_value}")


@app.command(name="state")
def _state(
    session_id: Annotated[
        str | None, Parameter(help="Session ID (defaults to CLAUDE_SESSION_ID env var)")
    ] = None,
    verbose: Annotated[
        bool, Parameter(help="Show full entry metadata for each key")
    ] = False,
) -> None:
    """Show all state in the session store

    Args:
        session_id: Optional session ID override
        verbose: Whether to show full entry metadata
    """
    store = _get_store(session_id)
    keys = list(store)

    if not keys:
        print("Session store is empty")
        return

    if verbose:
        for i, key in enumerate(keys):
            entry = store.get_entry(key)
            if entry is not None:
                if i > 0:
                    print("---")
                print(_format_entry_verbose(entry))
    else:
        for key in keys:
            value = store[key]
            print(f"{key}: {_format_value(value)}")


if __name__ == "__main__":
    app()
