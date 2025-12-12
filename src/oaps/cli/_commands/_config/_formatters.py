"""Output formatters for config commands."""

from typing import Any

from oaps.cli._commands._shared import format_json, format_table, format_yaml

# Type alias for configuration data - uses Any to match library signatures
ConfigData = dict[str, Any]  # pyright: ignore[reportExplicitAny]

__all__ = [
    "ConfigData",
    "ConfigValue",
    "format_json",
    "format_plain",
    "format_table",
    "format_toml",
    "format_yaml",
]


def format_toml(data: ConfigData) -> str:
    """Format data as TOML.

    Args:
        data: Dictionary to format as TOML.

    Returns:
        TOML-formatted string representation.
    """
    import tomli_w

    return tomli_w.dumps(data)


# Config value type - recursive type for nested config values
type ConfigValue = (
    None | bool | int | float | str | list[ConfigValue] | dict[str, ConfigValue]
)


def format_plain(value: ConfigValue) -> str:  # noqa: PLR0911
    """Format a value as plain text.

    Handles various types appropriately:
    - None: "null"
    - bool: "true" or "false"
    - numbers: string representation
    - strings: the string itself
    - lists: one item per line
    - dicts: key=value format, one per line

    Args:
        value: Any configuration value to format as plain text.

    Returns:
        Plain text string representation.
    """
    match value:
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case int() | float():
            return str(value)
        case str():
            return value
        case list():
            return "\n".join(format_plain(item) for item in value)
        case dict():
            return "\n".join(f"{k}={format_plain(v)}" for k, v in value.items())
        case _:  # pyright: ignore[reportUnnecessaryComparison]
            return str(value)  # pyright: ignore[reportUnreachable] Fallback for runtime
