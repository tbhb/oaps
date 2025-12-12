from typing import TYPE_CHECKING, cast

import orjson

if TYPE_CHECKING:
    from pathlib import Path


def load_json(json_str: str) -> dict[str, object] | list[object] | None:
    """Load and parse a JSON string.

    Args:
        json_str: The JSON string to parse.

    Returns:
        The parsed JSON data as a dictionary or list, or None if parsing fails.
    """
    try:
        return cast("dict[str, object] | list[object]", orjson.loads(json_str))
    except orjson.JSONDecodeError:
        return None


def load_json_file(file_path: Path) -> dict[str, object] | list[object] | None:
    """Load and parse a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        The parsed JSON data as a dictionary or list, or None if the file cannot be read.
    """  # noqa: E501
    return load_json(file_path.read_text())
