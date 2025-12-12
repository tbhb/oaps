# pyright: reportExplicitAny=false, reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""Configuration container with typed access.

This module provides the main Config class that serves as the primary
interface for accessing OAPS configuration values.
"""

from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, overload

import tomli_w
from pydantic import BaseModel, ConfigDict, PrivateAttr

from oaps.config._defaults import DEFAULT_CONFIG
from oaps.config._loader import copy_value, deep_merge, parse_env_vars, read_toml_file
from oaps.config._models._common import (
    ConfigSource,
    ConfigSourceName,
    LogFormat,
    LogLevel,
)
from oaps.config._models._ideas import IdeasConfiguration
from oaps.config._models._logging import LoggingConfig
from oaps.config._models._project import ProjectConfig

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Self

T = TypeVar("T")


def _parse_ideas(data: dict[str, Any]) -> IdeasConfiguration:
    """Parse ideas section dictionary into IdeasConfiguration.

    Args:
        data: Dictionary containing ideas configuration.

    Returns:
        Parsed IdeasConfiguration instance.
    """
    return IdeasConfiguration(
        tags=data.get("tags", {}),
        extend_tags=data.get("extend_tags", {}),
    )


def _parse_log_level(value: str) -> LogLevel:
    """Parse log level string to LogLevel enum, with fallback.

    Args:
        value: Log level string value.

    Returns:
        LogLevel enum value, defaulting to INFO for invalid values.
    """
    try:
        return LogLevel(value)
    except ValueError:
        return LogLevel.INFO


def _parse_log_format(value: str) -> LogFormat:
    """Parse log format string to LogFormat enum, with fallback.

    Args:
        value: Log format string value.

    Returns:
        LogFormat enum value, defaulting to JSON for invalid values.
    """
    try:
        return LogFormat(value)
    except ValueError:
        return LogFormat.JSON


def _parse_logging(data: dict[str, Any]) -> LoggingConfig:
    """Parse logging section dictionary into LoggingConfig.

    Args:
        data: Dictionary containing logging configuration.

    Returns:
        Parsed LoggingConfig instance.
    """
    return LoggingConfig(
        level=_parse_log_level(data.get("level", "info")),
        format=_parse_log_format(data.get("format", "json")),
        file=data.get("file", ""),
    )


def _parse_project(data: dict[str, Any]) -> ProjectConfig:
    """Parse project section dictionary into ProjectConfig.

    Args:
        data: Dictionary containing project configuration.

    Returns:
        Parsed ProjectConfig instance.
    """
    return ProjectConfig(
        name=data.get("name", ""),
        version=data.get("version", ""),
    )


class Config(BaseModel):
    """Configuration container with typed access.

    This class provides immutable, type-safe access to OAPS configuration.
    Use factory methods to create instances rather than the constructor.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    # Private attributes - not included in model fields
    _data: dict[str, Any] = PrivateAttr(default_factory=dict)
    _sources: tuple[ConfigSource, ...] = PrivateAttr(default=())
    _ideas: IdeasConfiguration = PrivateAttr(default_factory=IdeasConfiguration)
    _logging: LoggingConfig = PrivateAttr(default_factory=LoggingConfig)
    _project: ProjectConfig = PrivateAttr(default_factory=ProjectConfig)

    def __init__(
        self,
        *,
        _data: dict[str, Any] | None = None,
        _sources: tuple[ConfigSource, ...] = (),
        _ideas: IdeasConfiguration | None = None,
        _logging: LoggingConfig | None = None,
        _project: ProjectConfig | None = None,
    ) -> None:
        """Initialize configuration container.

        This constructor is intended for internal use. Use factory methods
        like from_dict(), from_file(), or load() to create Config instances.

        Args:
            _data: The complete merged configuration dictionary.
            _sources: Sources that contributed to this configuration.
            _ideas: Parsed ideas configuration section.
            _logging: Parsed logging configuration section.
            _project: Parsed project configuration section.
        """
        super().__init__()
        self._data = _data if _data is not None else {}
        self._sources = _sources
        self._ideas = _ideas if _ideas is not None else IdeasConfiguration()
        self._logging = _logging if _logging is not None else LoggingConfig()
        self._project = _project if _project is not None else ProjectConfig()

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        validate: bool = True,
    ) -> Self:
        """Create configuration from a dictionary.

        Args:
            data: Dictionary of configuration values.
            validate: Whether to validate the configuration.

        Returns:
            Configuration object from the dictionary.

        Raises:
            ConfigValidationError: If validation fails (when validate=True).
        """
        # Deferred import to avoid circular dependency
        from oaps.config._validation import (  # noqa: PLC0415
            raise_if_validation_errors,
            validate_config,
        )

        # 1. Merge with defaults to ensure all keys exist
        merged = deep_merge(DEFAULT_CONFIG, data)

        # 2. Validate if requested
        if validate:
            issues = validate_config(merged)
            raise_if_validation_errors(issues)

        # 3. Parse sections
        ideas_config = _parse_ideas(merged.get("ideas", {}))
        logging_config = _parse_logging(merged.get("logging", {}))
        project_config = _parse_project(merged.get("project", {}))

        # 4. Construct and return Config
        return cls(
            _data=merged,
            _sources=(),  # Empty for from_dict(), populated by from_file()/load()
            _ideas=ideas_config,
            _logging=logging_config,
            _project=project_config,
        )

    @classmethod
    def from_file(
        cls,
        path: Path,
        *,
        validate: bool = True,
    ) -> Self:
        """Load configuration from a specific file.

        Args:
            path: Path to the TOML config file.
            validate: Whether to validate the loaded config.

        Returns:
            Configuration object from the specified file only.

        Raises:
            FileNotFoundError: If the file does not exist.
            ConfigLoadError: If the file cannot be parsed.
            ConfigValidationError: If validation fails.
        """
        # Deferred import to avoid circular dependency
        from oaps.config._validation import (  # noqa: PLC0415
            raise_if_validation_errors,
            validate_config,
        )

        # 1. Read the TOML file (raises FileNotFoundError or ConfigLoadError)
        data = read_toml_file(path)

        # 2. Create source tracking
        source = ConfigSource(
            name=ConfigSourceName.PROJECT,  # Treat single file as project source
            path=path,
            exists=True,
            values=data,
        )

        # 3. Merge with defaults
        merged = deep_merge(DEFAULT_CONFIG, data)

        # 4. Validate if requested
        if validate:
            issues = validate_config(merged)
            raise_if_validation_errors(issues, source=str(path))

        # 5. Parse sections
        ideas_config = _parse_ideas(merged.get("ideas", {}))
        logging_config = _parse_logging(merged.get("logging", {}))
        project_config = _parse_project(merged.get("project", {}))

        # 6. Construct and return Config with source
        return cls(
            _data=merged,
            _sources=(source,),
            _ideas=ideas_config,
            _logging=logging_config,
            _project=project_config,
        )

    @property
    def sources(self) -> list[ConfigSource]:
        """Return the sources that contributed to this configuration.

        Returns:
            List of ConfigSource objects in precedence order.
        """
        return list(self._sources)

    @property
    def logging(self) -> LoggingConfig:
        """Return the logging configuration section."""
        return self._logging

    @property
    def project(self) -> ProjectConfig:
        """Return the project configuration section."""
        return self._project

    @property
    def ideas(self) -> IdeasConfiguration:
        """Return the ideas configuration section."""
        return self._ideas

    @classmethod
    def load(
        cls,
        *,
        project_root: Path | None = None,
        include_env: bool = True,
        include_cli: bool = False,
        cli_overrides: dict[str, Any] | None = None,
    ) -> Self:
        """Load merged configuration from all sources.

        Discovers all configuration sources and merges them in precedence order
        (defaults -> user -> project -> local -> worktree -> env -> cli).

        Args:
            project_root: Project root directory. If None, auto-detect by
                searching upward for `.oaps/` directory.
            include_env: Include environment variables as a source.
            include_cli: Include CLI overrides.
            cli_overrides: Dict of CLI argument overrides. Only used if
                include_cli is True.

        Returns:
            Merged configuration object.

        Raises:
            ConfigLoadError: If config files cannot be loaded.
            ConfigValidationError: If merged config fails validation.
        """
        # Deferred imports to avoid circular dependency
        from oaps.config._discovery import discover_sources  # noqa: PLC0415
        from oaps.config._validation import (  # noqa: PLC0415
            raise_if_validation_errors,
            validate_config,
        )

        # 1. Discover all sources (returned in highest-to-lowest precedence)
        sources = discover_sources(
            project_root=project_root,
            include_env=include_env,
            include_cli=include_cli,
            cli_overrides=cli_overrides,
        )

        # 2. Load and merge sources in precedence order (lowest to highest)
        # Sources are discovered highest-to-lowest, so reverse for merging
        merged: dict[str, Any] = {}
        loaded_sources: list[ConfigSource] = []

        for source in reversed(sources):
            values: dict[str, Any] = {}

            if source.name == ConfigSourceName.DEFAULT:
                # Default values are pre-populated
                values = source.values
            elif source.name == ConfigSourceName.ENV:
                # Parse environment variables
                if include_env:
                    values = parse_env_vars()
            elif source.name == ConfigSourceName.CLI:
                # CLI overrides are pre-populated
                if include_cli and cli_overrides:
                    values = cli_overrides
            elif source.path and source.exists:
                # File-based source - load from disk
                values = read_toml_file(source.path)

            # Create updated source with loaded values
            loaded_source = ConfigSource(
                name=source.name,
                path=source.path,
                exists=source.exists,
                values=values,
            )
            loaded_sources.append(loaded_source)

            # Merge values (only if non-empty)
            if values:
                merged = deep_merge(merged, values)

        # 3. Validate merged config
        issues = validate_config(merged)
        raise_if_validation_errors(issues)

        # 4. Parse sections
        ideas_config = _parse_ideas(merged.get("ideas", {}))
        logging_config = _parse_logging(merged.get("logging", {}))
        project_config = _parse_project(merged.get("project", {}))

        # 5. Construct and return Config
        # Sources in loaded_sources are lowest-to-highest, reverse for final list
        return cls(
            _data=merged,
            _sources=tuple(reversed(loaded_sources)),
            _ideas=ideas_config,
            _logging=logging_config,
            _project=project_config,
        )

    @overload
    def get(self, key: str) -> Any: ...

    @overload
    def get(self, key: str, default: T) -> T: ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key.

        Traverses nested dictionaries using dot notation to retrieve values.

        Args:
            key: Dot-notation key (e.g., "logging.level").
            default: Default value if key not found.

        Returns:
            The configuration value, or default if not found.

        Examples:
            >>> config.get("logging.level")
            'info'
            >>> config.get("nonexistent", "fallback")
            'fallback'
        """
        parts = key.split(".")
        current: Any = self._data

        for part in parts:
            if not isinstance(current, dict):
                return default
            if part not in current:
                return default
            current = current[part]

        return current

    def to_dict(self, *, include_defaults: bool = True) -> dict[str, Any]:
        """Convert configuration to a dictionary.

        Args:
            include_defaults: Whether to include default values. If False,
                only values that differ from defaults are included.

        Returns:
            Dictionary representation of the configuration.
        """
        if include_defaults:
            # Return a deep copy of the data
            return copy_value(self._data)

        # Filter out values that match defaults
        return _diff_from_defaults(self._data, DEFAULT_CONFIG)

    def to_toml(self, *, include_defaults: bool = False) -> str:
        """Convert configuration to a TOML string.

        Args:
            include_defaults: Whether to include default values. If False,
                only values that differ from defaults are included.

        Returns:
            TOML string representation of the configuration.
        """
        data = self.to_dict(include_defaults=include_defaults)
        return tomli_w.dumps(data)


def _diff_from_defaults(
    data: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    """Extract values that differ from defaults.

    Args:
        data: Current configuration data.
        defaults: Default configuration values.

    Returns:
        Dictionary containing only non-default values.
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        if key not in defaults:
            # Key not in defaults - include it (deep copy)
            result[key] = copy_value(value)
        elif isinstance(value, dict) and isinstance(defaults[key], dict):
            # Both are dicts - recurse
            nested_diff = _diff_from_defaults(value, defaults[key])
            if nested_diff:
                result[key] = nested_diff
        elif value != defaults[key]:
            # Value differs from default (deep copy)
            result[key] = copy_value(value)

    return result
