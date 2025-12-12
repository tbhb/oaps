import os
import sys
from typing import TYPE_CHECKING

from oaps.exceptions import ConfigError

from ._models import Config

if TYPE_CHECKING:
    from pathlib import Path


def safe_load_config(
    *,
    config_path: Path | None = None,
    project_root: Path | None = None,
    cli_overrides: dict[str, object] | None = None,
) -> tuple[Config, str | None]:
    """Load configuration with error handling.

    Attempts to load configuration and handles errors based on the
    OAPS_STRICT_CONFIG environment variable:
    - If unset or "0": warn to stderr and return empty config
    - If "1": fail fast with sys.exit(1)

    When config_path is provided, the file must exist (explicit user request).

    Args:
        config_path: Explicit path to config file (--config flag).
        project_root: Project root directory override (--project-root flag).
        cli_overrides: CLI argument overrides to pass to Config.load().

    Returns:
        Tuple of (Config, error_message). On success, error_message is None.
        On failure (non-strict mode), returns empty Config with error message.
    """
    strict_mode = os.environ.get("OAPS_STRICT_CONFIG", "0") == "1"

    try:
        if config_path is not None:
            # Explicit path - must exist
            if not config_path.exists():
                error_msg = f"Config file not found: {config_path}"
                # Always fail for explicit path
                print(f"Error: {error_msg}", file=sys.stderr)  # noqa: T201
                sys.exit(1)
            return Config.from_file(config_path), None

        # Normal load with discovery
        config = Config.load(
            project_root=project_root,
            include_env=True,
            include_cli=cli_overrides is not None,
            cli_overrides=cli_overrides,
        )
    except ConfigError as e:
        error_msg = str(e)
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)  # noqa: T201
            sys.exit(1)
        else:
            print(  # noqa: T201
                f"Warning: Failed to load config: {error_msg}",
                file=sys.stderr,
            )
            return Config.from_dict({}), error_msg
    except FileNotFoundError as e:
        error_msg = str(e)
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)  # noqa: T201
            sys.exit(1)
        else:
            print(  # noqa: T201
                f"Warning: Config file not found: {error_msg}",
                file=sys.stderr,
            )
            return Config.from_dict({}), error_msg
    except OSError as e:
        error_msg = f"Failed to load config: {e}"
        if strict_mode:
            print(f"Error: {error_msg}", file=sys.stderr)  # noqa: T201
            sys.exit(1)
        else:
            print(f"Warning: {error_msg}", file=sys.stderr)  # noqa: T201
            return Config.from_dict({}), error_msg
    else:
        return config, None
