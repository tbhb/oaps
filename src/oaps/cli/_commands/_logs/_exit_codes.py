"""Exit codes for logs commands."""

EXIT_SUCCESS: int = 0
"""Command completed successfully."""

EXIT_LOAD_ERROR: int = 1
"""Failed to load or parse log file."""

EXIT_SOURCE_NOT_FOUND: int = 2
"""Log source not found."""

EXIT_FILTER_ERROR: int = 3
"""Invalid filter expression."""
