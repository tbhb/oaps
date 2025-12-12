"""Output formatters for config commands."""

from typing import Any

# Type alias for configuration data - uses Any to match library signatures
ConfigData = dict[str, Any]  # pyright: ignore[reportExplicitAny]


def format_toml(data: ConfigData) -> str:
    """Format data as TOML.

    Args:
        data: Dictionary to format as TOML.

    Returns:
        TOML-formatted string representation.
    """
    import tomli_w

    return tomli_w.dumps(data)


def format_json(data: ConfigData, *, indent: bool = True) -> str:
    """Format data as JSON.

    Args:
        data: Dictionary to format as JSON.
        indent: Whether to pretty-print with indentation.

    Returns:
        JSON-formatted string representation.
    """
    import orjson

    options = orjson.OPT_INDENT_2 if indent else 0
    return orjson.dumps(data, option=options).decode("utf-8")


def format_yaml(data: ConfigData) -> str:
    """Format data as YAML.

    Args:
        data: Dictionary to format as YAML.

    Returns:
        YAML-formatted string representation.
    """
    import yaml

    return yaml.safe_dump(data, default_flow_style=False, allow_unicode=True)


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a Markdown table.

    Args:
        headers: Column headers for the table.
        rows: List of rows, where each row is a list of cell values.

    Returns:
        Markdown table string representation.
    """
    from pytablewriter import MarkdownTableWriter

    writer = MarkdownTableWriter(
        headers=headers,
        value_matrix=rows,
        margin=1,
    )
    return writer.dumps()


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
