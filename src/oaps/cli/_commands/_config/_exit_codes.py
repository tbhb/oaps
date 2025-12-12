"""Exit codes for config commands.

General exit codes:
    0 - Success
    1 - Load/parse error
    2 - Key error / invalid key-value
    3 - Validation error

Validate command exit codes (per CLI spec section 7.5):
    0 - Config is valid
    1 - Validation errors found
    2 - Warnings found with --strict (treated as errors)
"""

EXIT_SUCCESS: int = 0
"""Command completed successfully."""

EXIT_LOAD_ERROR: int = 1
"""Error loading or parsing configuration."""

EXIT_KEY_ERROR: int = 2
"""Key not found or invalid key/value."""

EXIT_VALIDATION_ERROR: int = 3
"""Configuration validation error."""

# Validate command-specific exit codes
# These differ from general exit codes per CLI spec section 7.5
EXIT_VALIDATE_ERRORS: int = 1
"""Validate command: validation errors found."""

EXIT_VALIDATE_STRICT_WARNINGS: int = 2
"""Validate command: warnings found with --strict (treated as errors)."""
