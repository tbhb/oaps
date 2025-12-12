"""Exit codes for analyze commands.

These codes follow Unix conventions and align with other OAPS command exit codes
for consistency across the CLI.
"""

EXIT_SUCCESS: int = 0
"""Command completed successfully."""

EXIT_LOAD_ERROR: int = 1
"""Failed to load or parse transcript files."""

EXIT_VALIDATION_ERROR: int = 2
"""Validation errors found in input data."""

EXIT_NOT_FOUND: int = 3
"""Specified transcript directory or session not found."""

EXIT_OUTPUT_ERROR: int = 4
"""Failed to write output files (reports, charts, parquet)."""
