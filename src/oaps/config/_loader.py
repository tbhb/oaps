# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""TOML configuration file loading and merging."""

import json
import os
import tomllib
from typing import TYPE_CHECKING, Any

from oaps.exceptions import ConfigLoadError

if TYPE_CHECKING:
    from pathlib import Path


def read_toml_file(path: Path) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Read and parse a TOML file.

    Args:
        path: Path to the TOML file.

    Returns:
        Parsed TOML content as dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        ConfigLoadError: If the file cannot be parsed.
    """
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        msg = f"Failed to parse TOML file: {e}"
        raise ConfigLoadError(
            msg,
            path=path,
            line=e.lineno,
            column=e.colno,
        ) from e


def deep_merge(
    base: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    override: dict[str, Any],  # pyright: ignore[reportExplicitAny]
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Deep merge two configuration dictionaries.

    Merges `override` into `base`, returning a new dictionary. Neither input
    is modified.

    Args:
        base: Base configuration (lower precedence).
        override: Override configuration (higher precedence).

    Returns:
        Merged configuration dictionary.

    Merge rules:
        - Dictionaries are recursively merged
        - Arrays are replaced entirely (no element-wise merge)
        - Scalars are replaced with override value
        - Missing keys in override preserve base values
    """
    result: dict[str, Any] = {}  # pyright: ignore[reportExplicitAny]

    # Get all keys from both dictionaries
    all_keys = set(base.keys()) | set(override.keys())

    for key in all_keys:
        if key not in override:
            # Key only in base - copy value
            result[key] = _copy_value(base[key])
        elif key not in base:
            # Key only in override - copy value
            result[key] = _copy_value(override[key])
        else:
            # Key in both - merge or replace
            base_val = base[key]
            override_val = override[key]

            if isinstance(base_val, dict) and isinstance(override_val, dict):
                # Both dicts - recurse
                result[key] = deep_merge(base_val, override_val)
            else:
                # Type mismatch or non-dicts - override wins
                result[key] = _copy_value(override_val)

    return result


def copy_value(value: Any) -> Any:  # pyright: ignore[reportExplicitAny]
    """Create a deep copy of a configuration value.

    Recursively copies dicts and lists to ensure the returned structure is
    fully independent of the original.

    Args:
        value: The value to copy.

    Returns:
        A deep copy of the value.
    """
    if isinstance(value, dict):
        # Recursively copy nested dicts
        return {k: copy_value(v) for k, v in value.items()}
    if isinstance(value, list):
        # Copy list elements
        return [copy_value(item) for item in value]
    # Primitives are immutable, no copy needed
    return value


# Alias for internal use within this module (used by deep_merge)
_copy_value = copy_value


def parse_env_vars(
    prefix: str = "OAPS_",
) -> dict[str, Any]:  # pyright: ignore[reportExplicitAny]
    """Parse environment variables into config dictionary.

    Args:
        prefix: Environment variable prefix (default: "OAPS_").

    Returns:
        Dictionary of parsed config values with nested structure.

    Environment variable naming:
        - Add prefix (OAPS_)
        - Convert to uppercase
        - Replace dots with double underscores
        - Example: logging.level -> OAPS_LOGGING__LEVEL
    """
    result: dict[str, Any] = {}  # pyright: ignore[reportExplicitAny]

    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        # Remove prefix and convert to config key path
        # OAPS_LOGGING__LEVEL -> logging.level
        config_key = key[len(prefix) :]
        if not config_key:
            continue

        # Convert double underscores to dots and lowercase
        config_path = config_key.replace("__", ".").lower()

        # Parse the value with type inference
        parsed_value = _parse_env_value(value)

        # Set the value at the nested path
        set_nested_key(result, config_path, parsed_value)

    return result


def _parse_env_value(value: str) -> Any:  # pyright: ignore[reportExplicitAny]
    """Parse environment variable value with type inference.

    Args:
        value: The raw string value from the environment variable.

    Returns:
        The parsed value with appropriate type.

    Order of type inference:
        1. Boolean: true/false/1/0 (case-insensitive)
        2. Integer: parseable as int
        3. Float: parseable as float (with decimal point)
        4. JSON array: starts with [ ends with ]
        5. JSON object: starts with { ends with }
        6. String: anything else
    """
    # 1. Boolean check (case-insensitive)
    lower_value = value.lower()
    if lower_value in ("true", "false", "1", "0"):
        return lower_value in ("true", "1")

    # 2. Integer check
    try:
        return int(value)
    except ValueError:
        pass

    # 3. Float check (must contain decimal point to distinguish from int)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass

    # 4. JSON array check
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # 5. JSON object check
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # 6. String (fallback)
    return value


def parse_string_value(value: str) -> Any:  # pyright: ignore[reportExplicitAny]
    """Parse a string value with automatic type inference.

    This function attempts to parse a string value into a more appropriate
    Python type using the following precedence:
    1. Boolean: true/false (case-insensitive)
    2. Integer: parseable as int (no decimal)
    3. Float: parseable as float (with decimal)
    4. JSON array/object: starts with [ or {
    5. String: fallback

    This is used both for environment variable parsing and CLI value parsing,
    providing consistent type inference across the configuration system.

    Args:
        value: Raw string value to parse.

    Returns:
        Parsed value with inferred type.

    Examples:
        >>> parse_string_value("true")
        True
        >>> parse_string_value("42")
        42
        >>> parse_string_value("3.14")
        3.14
        >>> parse_string_value("[1, 2, 3]")
        [1, 2, 3]
    """
    # 1. Boolean check (case-insensitive)
    lower_value = value.lower()
    if lower_value in ("true", "false"):
        return lower_value == "true"

    # 2. Integer check
    try:
        int_val = int(value)
        # Check if there's a decimal point (if so, should be float)
        if "." not in value:
            return int_val
    except ValueError:
        pass

    # 3. Float check (must contain decimal point to distinguish from int)
    if "." in value:
        try:
            return float(value)
        except ValueError:
            pass

    # 4. JSON array check
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # 5. JSON object check
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass

    # 6. String (fallback)
    return value


def set_nested_key(
    d: dict[str, Any],  # pyright: ignore[reportExplicitAny]
    key_path: str,
    value: Any,  # pyright: ignore[reportExplicitAny]
) -> None:
    """Set a value at a dotted key path in a nested dictionary.

    Creates intermediate dictionaries as needed.

    Args:
        d: The dictionary to modify.
        key_path: Dotted key path (e.g., "logging.level").
        value: The value to set.

    Example:
        >>> d = {}
        >>> set_nested_key(d, "logging.level", "debug")
        >>> d
        {'logging': {'level': 'debug'}}
    """
    parts = key_path.split(".")
    current = d

    # Navigate/create intermediate dicts
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            # Overwrite non-dict value with dict
            current[part] = {}
        current = current[part]

    # Set the final value
    if parts:
        current[parts[-1]] = value
