# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportExplicitAny=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportPrivateUsage=false
# ruff: noqa: D415, A002, TRY300, S603, PLR0911
"""Write commands for modifying OAPS configuration."""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import tomli_w
from cyclopts import Parameter

from oaps.config import (
    ConfigSourceName,
    discover_sources,
    parse_string_value,
    read_toml_file,
    set_nested_key,
    validate_config,
)
from oaps.exceptions import ConfigLoadError

from ._app import app
from ._exit_codes import (
    EXIT_KEY_ERROR,
    EXIT_LOAD_ERROR,
    EXIT_SUCCESS,
    EXIT_VALIDATION_ERROR,
)

if TYPE_CHECKING:
    from oaps.config._validation import ValidationIssue


# -----------------------------------------------------------------------------
# Enums
# -----------------------------------------------------------------------------


class ValueType(StrEnum):
    """Value type for config set command."""

    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    AUTO = "auto"


class FileSource(StrEnum):
    """Valid file sources for write operations."""

    LOCAL = "local"
    PROJECT = "project"
    USER = "user"


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _resolve_file_source(source_name: str) -> tuple[Path | None, str | None]:
    """Resolve source name to file path.

    Args:
        source_name: One of "project", "local", "user".

    Returns:
        Tuple of (path, error_message). On success, error is None.
        On failure, path is None and error contains message.
    """
    # Validate source name
    try:
        file_source = FileSource(source_name.lower())
    except ValueError:
        valid = ", ".join(s.value for s in FileSource)
        return None, f"Invalid file source '{source_name}'. Valid sources: {valid}"

    # Map FileSource to ConfigSourceName
    source_map = {
        FileSource.LOCAL: ConfigSourceName.LOCAL,
        FileSource.PROJECT: ConfigSourceName.PROJECT,
        FileSource.USER: ConfigSourceName.USER,
    }
    target_name = source_map[file_source]

    # Discover sources to get file paths
    sources = discover_sources()

    # Find the matching source
    for source in sources:
        if source.name == target_name:
            if source.path is None:
                return None, f"Source '{source_name}' does not have a file path"
            return source.path, None

    # Source not found - this happens when project root is not found
    # for project/local sources
    if file_source in (FileSource.LOCAL, FileSource.PROJECT):
        return None, (
            f"Cannot use '{source_name}' source: "
            "no .oaps/ directory found in current directory or parents"
        )

    return None, f"Source '{source_name}' not found"


def _parse_value_with_type(
    value: str,
    type_hint: ValueType,
) -> tuple[Any, str | None]:
    """Parse string value with type coercion.

    Args:
        value: Raw string value from CLI.
        type_hint: Requested type or "auto" for inference.

    Returns:
        Tuple of (parsed_value, error_message). On success, error is None.
    """
    match type_hint:
        case ValueType.STRING:
            return value, None

        case ValueType.INT:
            try:
                return int(value), None
            except ValueError:
                return None, f"Cannot parse '{value}' as integer"

        case ValueType.FLOAT:
            try:
                return float(value), None
            except ValueError:
                return None, f"Cannot parse '{value}' as float"

        case ValueType.BOOL:
            lower_value = value.lower()
            if lower_value in ("true", "1", "yes", "on"):
                return True, None
            if lower_value in ("false", "0", "no", "off"):
                return False, None
            return None, f"Cannot parse '{value}' as boolean (use true/false/1/0)"

        case ValueType.AUTO:
            return _infer_value_type(value), None


def _infer_value_type(value: str) -> Any:
    """Infer the type of a string value.

    Uses the shared parse_string_value function from the config module
    which provides consistent type inference across the configuration system.

    Args:
        value: Raw string value.

    Returns:
        Parsed value with inferred type.
    """
    return parse_string_value(value)


def _read_or_create_config(path: Path) -> tuple[dict[str, Any], str | None]:
    """Read existing config or prepare for creation.

    Args:
        path: Path to config file.

    Returns:
        Tuple of (config_dict, error_message). On success, error is None.
    """
    if not path.exists():
        return {}, None

    try:
        return read_toml_file(path), None
    except ConfigLoadError as e:
        return {}, f"Failed to parse existing config: {e}"


def _write_config_file(path: Path, data: dict[str, Any]) -> str | None:
    """Write configuration to file atomically.

    Creates parent directories if they do not exist. Uses atomic
    write pattern (write to temp, then rename).

    Args:
        path: Destination file path.
        data: Configuration dictionary to write.

    Returns:
        Error message on failure, None on success.
    """
    try:
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate TOML content
        content = tomli_w.dumps(data)

        # Write to temp file in same directory, then rename (atomic on POSIX)
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            delete=False,
            suffix=".tmp",
            encoding="utf-8",
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # On Windows, need to remove target first
            if sys.platform == "win32" and path.exists():
                path.unlink()

            temp_path.rename(path)
        except OSError:
            # Clean up temp file on rename failure
            temp_path.unlink(missing_ok=True)
            raise

        return None

    except OSError as e:
        return f"Failed to write config file: {e}"


def _validate_after_write() -> list[ValidationIssue]:
    """Validate merged configuration after modification.

    Returns:
        List of validation issues (errors only).
    """
    from oaps.config import Config

    try:
        # Load merged config from all sources
        Config.load()
        return []
    except Exception as e:  # noqa: BLE001
        # Create a synthetic validation issue
        from oaps.config._validation import ValidationIssue

        return [
            ValidationIssue(
                severity="error",
                key="",
                message=str(e),
                source=None,
                actual=None,
                expected=None,
            )
        ]


def _find_editor() -> tuple[list[str], str | None]:
    """Find editor command to use.

    Checks environment variables in order:
    1. $OAPS_EDITOR
    2. $VISUAL
    3. $EDITOR
    4. Platform default (open on macOS, xdg-open on Linux, start on Windows)

    Returns:
        Tuple of (command_parts, error_message). On success, error is None.
    """
    # Check environment variables in order
    for env_var in ("OAPS_EDITOR", "VISUAL", "EDITOR"):
        editor = os.environ.get(env_var)
        if editor:
            # Split the command (handles "code --wait" style values)
            parts = shlex.split(editor)
            # Verify the command exists
            if parts and shutil.which(parts[0]):
                return parts, None
            # Command not found or empty, continue to next option

    # Platform defaults
    match sys.platform:
        case "darwin":
            # macOS: use open command
            return ["open"], None
        case "win32":
            # Windows: use start command
            # Empty string after "start" is for the title argument
            return ["cmd", "/c", "start", ""], None
        case _:
            # Linux and others: use xdg-open if available
            if shutil.which("xdg-open"):
                return ["xdg-open"], None

    return [], "No editor found. Set $EDITOR or $VISUAL environment variable."


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command(name="set")
def _set(
    key: str,
    value: str,
    /,
    *,
    file: Annotated[
        FileSource,
        Parameter(
            name=["--file", "-f"],
            help="Target file: project, local (default), or user",
        ),
    ] = FileSource.LOCAL,
    type: Annotated[
        ValueType,
        Parameter(
            name=["--type", "-t"],
            help="Value type: string, int, float, bool, or auto (default)",
        ),
    ] = ValueType.AUTO,
) -> None:
    """Set a configuration value

    Sets a configuration value in the specified config file. The key
    uses dot notation for nested values (e.g., logging.level).

    Args:
        key: Dot-notation key path (e.g., logging.level).
        value: Value to set.
        file: Target file (project, local, user).
        type: Value type for parsing (auto infers type).
    """
    # 1. Resolve file path
    path, error = _resolve_file_source(file.value)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    if path is None:
        print("Error: Could not resolve file path")
        raise SystemExit(EXIT_LOAD_ERROR)

    # 2. Parse value with type
    parsed_value, error = _parse_value_with_type(value, type)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_KEY_ERROR)

    # 3. Read existing config or start fresh
    config_data, error = _read_or_create_config(path)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    # 4. Set the key using dot notation
    set_nested_key(config_data, key, parsed_value)

    # 5. Validate the modified config before writing
    issues = validate_config(config_data)
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        issue = errors[0]
        print(f"Error: Invalid value for '{issue.key}': {issue.message}")
        raise SystemExit(EXIT_VALIDATION_ERROR)

    # 6. Write the config file
    error = _write_config_file(path, config_data)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    # 7. Validate merged config after write
    validation_issues = _validate_after_write()
    if validation_issues:
        issue = validation_issues[0]
        print(f"Warning: Configuration may be invalid: {issue.message}")
        # Don't fail - the file was written successfully, but merged config
        # might have issues from other sources

    print(f"Set {key} = {parsed_value!r} in {path}")
    raise SystemExit(EXIT_SUCCESS)


@app.command(name="edit")
def _edit(
    *,
    file: Annotated[
        FileSource,
        Parameter(
            name=["--file", "-f"],
            help="File to edit: project, local (default), or user",
        ),
    ] = FileSource.LOCAL,
    create: Annotated[
        bool,
        Parameter(
            name="--create",
            help="Create the file if it doesn't exist",
        ),
    ] = False,
) -> None:
    """Open a config file in an editor

    Opens the specified configuration file in your preferred editor.
    Editor is selected from $OAPS_EDITOR, $VISUAL, $EDITOR, or
    platform default (open/xdg-open/start).

    Args:
        file: Target file (project, local, user).
        create: Create the file if it doesn't exist.
    """
    # 1. Resolve file path
    path, error = _resolve_file_source(file.value)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    if path is None:
        print("Error: Could not resolve file path")
        raise SystemExit(EXIT_LOAD_ERROR)

    # 2. Check if file exists
    if not path.exists():
        if create:
            # Create empty file
            error = _write_config_file(path, {})
            if error:
                print(f"Error: {error}")
                raise SystemExit(EXIT_LOAD_ERROR)
            print(f"Created {path}")
        else:
            print(f"Error: File not found: {path}")
            print("Use --create to create a new config file")
            raise SystemExit(EXIT_LOAD_ERROR)

    # 3. Find editor
    editor_cmd, error = _find_editor()
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_KEY_ERROR)

    # 4. Launch editor
    try:
        cmd = [*editor_cmd, str(path)]
        subprocess.run(cmd, check=False)
    except OSError as e:
        print(f"Error: Failed to launch editor: {e}")
        raise SystemExit(EXIT_KEY_ERROR) from None

    raise SystemExit(EXIT_SUCCESS)
