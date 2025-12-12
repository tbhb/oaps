"""Exit codes for command subcommands.

Following Claude Code conventions:
- 0: Success
- 1: Load/parse error
- 2: Validation error
- 3: Not found
"""

EXIT_SUCCESS: int = 0
EXIT_LOAD_ERROR: int = 1
EXIT_VALIDATION_ERROR: int = 2
EXIT_NOT_FOUND: int = 3
