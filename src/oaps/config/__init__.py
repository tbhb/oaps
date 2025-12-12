"""OAPS configuration.

This module provides the public API for OAPS configuration management,
including loading, validation, and typed access to configuration values.

Example:
    >>> from oaps.config import Config
    >>> config = Config.load()
    >>> config.logging.level
    <LogLevel.INFO: 'info'>
"""

# Re-export exceptions from main exceptions module
from oaps.exceptions import (
    ConfigError,
    ConfigLoadError,
    ConfigValidationError,
)

# Defaults
from ._defaults import DEFAULT_CONFIG

# Discovery utilities
from ._discovery import (
    discover_sources,
    find_project_root,
    get_git_dir,
    get_user_config_path,
)

# Hook rule loading
from ._hooks_loader import (
    discover_drop_in_files,
    load_all_hook_rules,
    load_drop_in_rules,
    load_hooks_configuration,
    merge_hook_rules,
)
from ._load import safe_load_config

# Loader utilities
from ._loader import deep_merge, parse_string_value, read_toml_file, set_nested_key

# All models from the _models subpackage
from ._models import (
    ArtifactPrefixConfiguration,
    Config,
    ConfigSource,
    ConfigSourceName,
    HookRuleActionConfiguration,
    HookRuleConfiguration,
    HooksConfiguration,
    IdeasConfiguration,
    LogFormat,
    LoggingConfig,
    LogLevel,
    ProjectConfig,
    RequirementPrefixConfiguration,
    RulePriority,
    SpecConfiguration,
    SpecNumberingConfiguration,
    SpecPrefixesConfiguration,
    SpecStatusesConfiguration,
    StorageConfiguration,
    TestPrefixConfiguration,
)

# Storage loading
from ._storage_loader import load_storage_configuration

# Validation
from ._validation import (
    ValidationIssue,
    get_config_schema,
    raise_if_validation_errors,
    validate_config,
    validate_source,
)

__all__ = [
    "DEFAULT_CONFIG",
    "ArtifactPrefixConfiguration",
    "Config",
    "ConfigError",
    "ConfigLoadError",
    "ConfigSource",
    "ConfigSourceName",
    "ConfigValidationError",
    "HookRuleActionConfiguration",
    "HookRuleConfiguration",
    "HooksConfiguration",
    "IdeasConfiguration",
    "LogFormat",
    "LogLevel",
    "LoggingConfig",
    "ProjectConfig",
    "RequirementPrefixConfiguration",
    "RulePriority",
    "SpecConfiguration",
    "SpecNumberingConfiguration",
    "SpecPrefixesConfiguration",
    "SpecStatusesConfiguration",
    "StorageConfiguration",
    "TestPrefixConfiguration",
    "ValidationIssue",
    "deep_merge",
    "discover_drop_in_files",
    "discover_sources",
    "find_project_root",
    "get_config_schema",
    "get_git_dir",
    "get_user_config_path",
    "load_all_hook_rules",
    "load_drop_in_rules",
    "load_hooks_configuration",
    "load_storage_configuration",
    "merge_hook_rules",
    "parse_string_value",
    "raise_if_validation_errors",
    "read_toml_file",
    "safe_load_config",
    "set_nested_key",
    "validate_config",
    "validate_source",
]
