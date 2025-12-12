# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportExplicitAny=false, reportAny=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
# ruff: noqa: D415, A002, PLR0911, TRY300, TC003
"""Read commands for viewing OAPS configuration."""

from pathlib import Path
from typing import Annotated, Any

from cyclopts import Parameter

from oaps.cli._commands._context import OutputFormat
from oaps.config import (
    Config,
    ConfigLoadError,
    ConfigSource,
    ConfigSourceName,
    discover_sources,
    get_config_schema,
)
from oaps.exceptions import ConfigValidationError

from ._app import app
from ._exit_codes import EXIT_KEY_ERROR, EXIT_LOAD_ERROR, EXIT_SUCCESS
from ._formatters import (
    ConfigData,
    format_json,
    format_plain,
    format_table,
    format_toml,
    format_yaml,
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _resolve_source_name(name: str) -> ConfigSourceName | None:
    """Convert a source name string to ConfigSourceName enum.

    Args:
        name: The source name string (case-insensitive).

    Returns:
        The ConfigSourceName enum value, or None if invalid.
    """
    try:
        return ConfigSourceName(name.lower())
    except ValueError:
        return None


def _load_config_for_source(
    source_name: str | None,
) -> tuple[Config | None, str | None]:
    """Load configuration, optionally filtered to a specific source.

    Args:
        source_name: Source name to filter to, or None for all sources.

    Returns:
        Tuple of (Config or None, error message or None).
    """
    try:
        if source_name is None:
            # Load all sources
            config = Config.load()
            return config, None

        # Validate source name
        resolved = _resolve_source_name(source_name)
        if resolved is None:
            valid = ", ".join(s.value for s in ConfigSourceName)
            return None, f"Invalid source '{source_name}'. Valid sources: {valid}"

        # Find the source and load just that source's config
        sources = discover_sources()
        target_source: ConfigSource | None = None
        for source in sources:
            if source.name == resolved:
                target_source = source
                break

        if target_source is None:
            return None, f"Source '{source_name}' not found"

        if not target_source.exists:
            return None, f"Source '{source_name}' does not exist"

        # For file-based sources, load from file
        if target_source.path:
            config = Config.from_file(target_source.path, validate=False)
            return config, None

        # For non-file sources (DEFAULT, ENV, CLI), return values directly
        if target_source.values:
            config = Config.from_dict(target_source.values, validate=False)
            return config, None

        return None, f"Source '{source_name}' has no values"

    except ConfigLoadError as e:
        return None, f"Failed to load config: {e}"
    except ConfigValidationError as e:
        return None, f"Config validation failed: {e}"


def _track_value_sources(
    sources: list[ConfigSource],
) -> dict[str, str]:
    """Build a mapping of key paths to source names.

    For each key in the configuration, determines which source provided
    that value (highest precedence wins).

    Args:
        sources: List of ConfigSource objects (highest precedence first).

    Returns:
        Dict mapping dot-notation key paths to source names.
    """
    source_map: dict[str, str] = {}

    def _add_keys(
        values: ConfigData,
        prefix: str,
        source_name: str,
    ) -> None:
        """Recursively add keys from a dict to the source map."""
        for key, value in values.items():
            full_key = f"{prefix}.{key}" if prefix else key
            # Only add if not already set (higher precedence wins)
            if full_key not in source_map:
                source_map[full_key] = source_name
            # Recurse into nested dicts
            if isinstance(value, dict):
                _add_keys(value, full_key, source_name)

    # Process sources in precedence order (highest first)
    for source in sources:
        if source.exists and source.values:
            _add_keys(source.values, "", source.name.value)

    return source_map


def _annotate_with_sources_toml(
    output: str,
    source_map: dict[str, str],
) -> str:
    """Add source comments to TOML output.

    Args:
        output: The TOML formatted string.
        source_map: Dict mapping key paths to source names.

    Returns:
        TOML string with source comments appended to each line.
    """
    lines = output.split("\n")
    result: list[str] = []
    current_section = ""

    for line in lines:
        stripped = line.strip()

        # Track current section
        if stripped.startswith("[") and stripped.endswith("]"):
            # Extract section name, handling nested sections like [hooks.rules]
            current_section = stripped[1:-1]
            result.append(line)
            continue

        # Skip empty lines and pure comments
        if not stripped or stripped.startswith("#"):
            result.append(line)
            continue

        # Parse key = value lines
        if "=" in line:
            key_part = line.split("=", 1)[0].strip()
            full_key = f"{current_section}.{key_part}" if current_section else key_part

            # Find source for this key
            source = source_map.get(full_key, "unknown")
            result.append(f"{line}  # source: {source}")
        else:
            result.append(line)

    return "\n".join(result)


def _annotate_with_sources_yaml(
    output: str,
    source_map: dict[str, str],
) -> str:
    """Add source comments to YAML output.

    Args:
        output: The YAML formatted string.
        source_map: Dict mapping key paths to source names.

    Returns:
        YAML string with source comments appended to each line.
    """
    lines = output.split("\n")
    result: list[str] = []
    key_stack: list[str] = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            result.append(line)
            continue

        # Calculate indentation level
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        indent_level = indent // 2  # YAML typically uses 2-space indentation

        # Trim stack to current level
        key_stack = key_stack[:indent_level]

        # Parse key: value or key:
        if ":" in stripped:
            key_part = stripped.split(":", 1)[0]
            key_stack.append(key_part)
            full_key = ".".join(key_stack)

            # Find source for this key
            source = source_map.get(full_key)
            if source:
                # Only add comment if there's a value on the same line
                if stripped.split(":", 1)[1].strip():
                    result.append(f"{line}  # source: {source}")
                else:
                    result.append(line)
            else:
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


def _get_nested_value(
    data: ConfigData,
    key: str,
) -> tuple[Any, bool]:
    """Get a nested value from a dictionary using dot notation.

    Args:
        data: The dictionary to search.
        key: Dot-notation key path.

    Returns:
        Tuple of (value, found). If found is False, value is None.
    """
    parts = key.split(".")
    current: Any = data

    for part in parts:
        if not isinstance(current, dict):
            return None, False
        if part not in current:
            return None, False
        current = current[part]

    return current, True


def _filter_to_section(
    data: ConfigData,
    section: str,
) -> ConfigData | None:
    """Filter config data to a specific section.

    Args:
        data: The full configuration dictionary.
        section: The section name (e.g., "logging", "project").

    Returns:
        The section dict, or None if not found.
    """
    if section in data and isinstance(data[section], dict):
        return {section: data[section]}
    return None


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------


@app.command(name="show")
def _show(
    *,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (toml, json, yaml)",
        ),
    ] = OutputFormat.TOML,
    source: Annotated[
        str | None,
        Parameter(
            name=["--source", "-s"],
            help="Show config from specific source only",
        ),
    ] = None,
    section: Annotated[
        str | None,
        Parameter(
            name=["--section"],
            help="Show specific section only (e.g., logging, project)",
        ),
    ] = None,
    no_defaults: Annotated[
        bool,
        Parameter(
            name="--no-defaults",
            help="Exclude default values",
        ),
    ] = False,
    show_sources: Annotated[
        bool,
        Parameter(
            name="--show-sources",
            help="Annotate output with source comments (TOML/YAML only)",
        ),
    ] = False,
) -> None:
    """Display merged configuration

    Shows the current merged configuration from all sources in the
    specified format. Use --source to view config from a single source,
    or --section to view a specific section.

    Args:
        format: Output format (toml, json, yaml).
        source: Specific source to show (e.g., project, user, local).
        section: Specific section to show (e.g., logging, project).
        no_defaults: Exclude default values from output.
        show_sources: Add source annotations (TOML/YAML only).
    """
    # Validate show-sources with JSON format
    if show_sources and format == OutputFormat.JSON:
        print("Error: --show-sources is not supported with JSON format")
        raise SystemExit(EXIT_LOAD_ERROR)

    # Load configuration
    config, error = _load_config_for_source(source)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    if config is None:
        print("Error: Failed to load configuration")
        raise SystemExit(EXIT_LOAD_ERROR)

    # Get data as dict
    data = config.to_dict(include_defaults=not no_defaults)

    # Filter to section if requested
    if section:
        filtered = _filter_to_section(data, section)
        if filtered is None:
            print(f"Error: Section '{section}' not found")
            raise SystemExit(EXIT_LOAD_ERROR)
        data = filtered

    # Build source map if needed
    source_map: dict[str, str] = {}
    if show_sources:
        # Always discover sources for accurate source tracking
        # When filtering to specific source, we still show merged config source info
        sources_list = discover_sources()
        source_map = _track_value_sources(sources_list)

    # Format output
    match format:
        case OutputFormat.TOML:
            output = format_toml(data)
            if show_sources:
                output = _annotate_with_sources_toml(output, source_map)
        case OutputFormat.JSON:
            output = format_json(data)
        case OutputFormat.YAML:
            output = format_yaml(data)
            if show_sources:
                output = _annotate_with_sources_yaml(output, source_map)
        case _:
            # Fallback for any other format
            output = format_toml(data)

    print(output.rstrip())
    raise SystemExit(EXIT_SUCCESS)


@app.command(name="get")
def _get(
    key: str,
    /,
    *,
    source: Annotated[
        str | None,
        Parameter(
            name=["--source", "-s"],
            help="Get value from specific source only",
        ),
    ] = None,
    default: Annotated[
        str | None,
        Parameter(
            name=["--default", "-d"],
            help="Default value if key not found",
        ),
    ] = None,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (plain, json)",
        ),
    ] = OutputFormat.PLAIN,
) -> None:
    """Get a specific configuration value

    Retrieves a configuration value by dot-notation key path.
    Nested values are returned as JSON when using --format json.

    Args:
        key: Dot-notation key path (e.g., logging.level).
        source: Specific source to get value from.
        default: Default value if key not found.
        format: Output format (plain, json).
    """
    # Load configuration
    config, error = _load_config_for_source(source)
    if error:
        print(f"Error: {error}")
        raise SystemExit(EXIT_LOAD_ERROR)

    if config is None:
        print("Error: Failed to load configuration")
        raise SystemExit(EXIT_LOAD_ERROR)

    # Get data and look up key
    data = config.to_dict()
    value, found = _get_nested_value(data, key)

    if not found:
        if default is not None:
            print(default)
            raise SystemExit(EXIT_SUCCESS)
        print(f"Error: Key '{key}' not found")
        raise SystemExit(EXIT_KEY_ERROR)

    # Format output
    if format == OutputFormat.JSON:
        # Wrap primitives in a dict for JSON output
        if isinstance(value, dict):
            output = format_json(value)
        else:
            # For primitives, output JSON value directly
            import orjson

            output = orjson.dumps(value).decode("utf-8")
        print(output)
    else:
        # Plain format
        output = format_plain(value)
        print(output)

    raise SystemExit(EXIT_SUCCESS)


@app.command(name="list-sources")
def _list_sources(
    *,
    all_sources: Annotated[
        bool,
        Parameter(
            name=["--all", "-a"],
            help="Include non-existent sources",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (table, json, plain)",
        ),
    ] = OutputFormat.TABLE,
) -> None:
    """List configuration sources

    Shows all configuration sources in precedence order (highest first).
    Use --all to include sources that don't exist yet.

    Args:
        all_sources: Include non-existent sources in the list.
        format: Output format (table, json, plain).
    """
    try:
        sources = discover_sources()
    except (ConfigLoadError, OSError) as e:
        print(f"Error: Failed to discover sources: {e}")
        raise SystemExit(EXIT_LOAD_ERROR) from None

    # Filter to existing sources unless --all is specified
    if not all_sources:
        sources = [s for s in sources if s.exists]

    if format == OutputFormat.JSON:
        # JSON format
        data: list[ConfigData] = []
        for source in sources:
            entry: ConfigData = {
                "name": source.name.value,
                "path": str(source.path) if source.path else None,
                "exists": source.exists,
            }
            data.append(entry)
        output = format_json({"sources": data})
        print(output)
    elif format == OutputFormat.PLAIN:
        # Plain format: one source per line
        for source in sources:
            path_str = str(source.path) if source.path else "(no path)"
            exists_str = "" if source.exists else " (not found)"
            print(f"{source.name.value}: {path_str}{exists_str}")
    else:
        # Table format (default)
        headers = ["Source", "Path", "Exists"]
        rows: list[list[str]] = []
        for source in sources:
            path_str = str(source.path) if source.path else "-"
            exists_str = "yes" if source.exists else "no"
            rows.append([source.name.value, path_str, exists_str])
        output = format_table(headers, rows)
        print(output.rstrip())

    raise SystemExit(EXIT_SUCCESS)


@app.command(name="schema")
def _schema(
    *,
    output: Annotated[
        Path | None,
        Parameter(
            name=["--output", "-o"],
            help="Write schema to file instead of stdout",
        ),
    ] = None,
    format: Annotated[
        OutputFormat,
        Parameter(
            name=["--format", "-f"],
            help="Output format (json, yaml)",
        ),
    ] = OutputFormat.JSON,
) -> None:
    """Output the configuration JSON Schema

    Outputs the JSON Schema describing the structure of OAPS
    configuration files. Useful for IDE validation and documentation.

    Args:
        output: File path to write schema to.
        format: Output format (json, yaml).
    """
    # Get schema
    schema_dict: ConfigData = get_config_schema()

    # Format schema
    if format == OutputFormat.YAML:
        formatted = format_yaml(schema_dict)
    else:
        formatted = format_json(schema_dict)

    # Output
    if output:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(formatted)
            print(f"Schema written to {output}")
        except OSError as e:
            print(f"Error: Failed to write schema: {e}")
            raise SystemExit(EXIT_LOAD_ERROR) from None
    else:
        print(formatted.rstrip())

    raise SystemExit(EXIT_SUCCESS)
