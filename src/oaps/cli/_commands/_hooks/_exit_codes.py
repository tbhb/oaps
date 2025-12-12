"""Exit codes for hooks commands.

These codes follow Unix conventions and align with the config command exit codes
for consistency across the CLI.
"""

EXIT_SUCCESS: int = 0
"""Command completed successfully."""

EXIT_LOAD_ERROR: int = 1
"""Failed to load or parse hook rules from configuration files."""

EXIT_VALIDATION_ERROR: int = 2
"""Hook rule validation errors found (schema, expression syntax, etc.)."""

EXIT_NOT_FOUND: int = 3
"""Specified rule ID or resource not found."""

EXIT_INPUT_ERROR: int = 4
"""Invalid input provided (bad JSON, missing required fields, etc.)."""
