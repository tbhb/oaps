# Automation scripts examples

This document provides complete TOML examples for `script` and `python` actions that execute external code for side effects, validation, notifications, and complex processing logic.

## Script action examples

The `script` action executes shell commands or scripts with optional JSON context on stdin.

### Run shell command on file write

Log file writes to a tracking system:

```toml
[[rules]]
id = "track-file-writes"
description = "Log all file writes to tracking system"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Write"'
result = "ok"

[[rules.actions]]
type = "script"
command = "echo \"$(date -Iseconds) WRITE ${tool_input.file_path}\" >> /tmp/claude-file-writes.log"
timeout_ms = 2000
```

### Execute linter on code changes

Run linting after Python file modifications:

```toml
[[rules]]
id = "lint-on-python-write"
description = "Run ruff check after writing Python files"
events = ["post_tool_use"]
priority = "medium"
condition = '''
tool_name == "Write" and $matches_glob(tool_input.file_path, "*.py")
'''
result = "ok"

[[rules.actions]]
type = "script"
command = "uv run ruff check ${tool_input.file_path} --output-format=concise 2>&1 | head -20"
timeout_ms = 30000
stdout = "log"
stderr = "append_to_stdout"
```

### Send notification via curl

Post to Slack when deployment commands are detected:

```toml
[[rules]]
id = "notify-deploy-attempt"
description = "Send Slack notification on deploy commands"
events = ["pre_tool_use"]
priority = "low"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "deploy|kubectl apply|terraform apply"
'''
result = "ok"

[[rules.actions]]
type = "script"
command = '''
curl -s -X POST "$SLACK_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{\"text\": \"Deploy command detected: ${tool_input.command}\"}"
'''
timeout_ms = 5000
env = { SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" }
```

### Environment variables and working directory

Execute script with custom environment and cwd:

```toml
[[rules]]
id = "custom-env-script"
description = "Run script with custom environment"
events = ["post_tool_use"]
priority = "low"
condition = 'tool_name == "Bash" and tool_input.command =~~ "npm test|pytest"'
result = "ok"

[[rules.actions]]
type = "script"
command = "./scripts/report-test-run.sh"
cwd = "/Users/tony/projects/myapp"
timeout_ms = 10000
env = { CI = "true", REPORT_LEVEL = "summary", NODE_ENV = "test" }
stdout = "log"
```

### Timeout handling

Long-running validation with extended timeout:

```toml
[[rules]]
id = "security-scan"
description = "Run security scan on package installations"
events = ["post_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and (
    tool_input.command =~~ "npm install|pip install|cargo add"
)
'''
result = "ok"

[[rules.actions]]
type = "script"
# Security scan may take time - use 2 minute timeout
command = "npm audit --json 2>/dev/null | jq -r '.vulnerabilities | keys[]' | head -5"
timeout_ms = 120000
stdout = "log"
stderr = "log"
```

### Stdin/stdout/stderr handling

Pass context JSON to script and process output:

```toml
[[rules]]
id = "custom-validation-script"
description = "Run custom validation with full context"
events = ["pre_tool_use"]
priority = "high"
condition = 'tool_name == "Bash"'
result = "ok"

[[rules.actions]]
type = "script"
stdin = "json"
stdout = "log"
stderr = "log"
script = """
#!/bin/bash
# Read JSON context from stdin
context=$(cat)

# Extract command from context
command=$(echo "$context" | jq -r '.tool_input.command // ""')
cwd=$(echo "$context" | jq -r '.cwd // ""')

# Validate command does not access sensitive directories
if [[ "$command" =~ /etc/passwd|/etc/shadow|\.ssh/id_ ]]; then
    # Return JSON to deny the operation
    echo '{"deny": true, "deny_message": "Access to sensitive files is not allowed"}'
    exit 0
fi

# Log command for auditing
echo "[AUDIT] Command: $command in $cwd" >&2

# No output means allow (fail-open)
"""
timeout_ms = 5000
```

## Python action examples

The `python` action executes Python functions in-process with direct access to the HookContext.

### Module:function format for entrypoint

Basic Python validation function:

```toml
[[rules]]
id = "python-path-validator"
description = "Validate file paths using Python"
events = ["pre_tool_use"]
priority = "high"
condition = '''
(tool_name == "Write" or tool_name == "Edit") and tool_input.file_path != null
'''
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.validators:validate_file_path"
timeout_ms = 5000
```

The Python module (`my_hooks/validators.py`):

```python
"""Hook validators for OAPS."""

from pathlib import Path


def validate_file_path(context):
    """Validate that file paths are within allowed directories.

    Args:
        context: HookContext with hook_input containing tool_input.

    Returns:
        Dict with deny/warn keys, or None to allow.
    """
    tool_input = context.hook_input.tool_input
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return None

    path = Path(file_path).resolve()
    cwd = Path(context.hook_input.cwd).resolve()

    # Block writes outside project directory
    if not path.is_relative_to(cwd):
        return {
            "deny": True,
            "deny_message": f"Cannot write to {path} - outside project directory"
        }

    # Warn about writing to sensitive files
    sensitive_patterns = [".env", "secrets", "credentials", ".pem", ".key"]
    if any(pat in path.name.lower() for pat in sensitive_patterns):
        return {"warn": f"Writing to potentially sensitive file: {path.name}"}

    return None
```

### Receiving context via stdin JSON

Python function that processes the full hook context:

```toml
[[rules]]
id = "python-command-analyzer"
description = "Analyze bash commands for security risks"
events = ["pre_tool_use"]
priority = "critical"
condition = 'tool_name == "Bash"'
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.security:analyze_command"
timeout_ms = 10000
```

Python implementation:

```python
"""Security analysis for hook commands."""

import re
from dataclasses import dataclass


@dataclass
class RiskPattern:
    """A pattern that indicates security risk."""
    pattern: str
    severity: str  # "block", "warn"
    message: str


RISK_PATTERNS = [
    RiskPattern(r"rm\s+-rf\s+/(?!\w)", "block", "Dangerous rm -rf on root"),
    RiskPattern(r"chmod\s+777", "warn", "Overly permissive chmod 777"),
    RiskPattern(r"curl.*\|\s*(?:ba)?sh", "block", "Piping curl to shell"),
    RiskPattern(r"eval\s+\$", "warn", "Eval with variable expansion"),
    RiskPattern(r">\s*/dev/sd[a-z]", "block", "Direct write to block device"),
]


def analyze_command(context):
    """Analyze command for security risks.

    Args:
        context: HookContext from the hook system.

    Returns:
        Dict with deny/warn, or None if safe.
    """
    tool_input = context.hook_input.tool_input
    command = tool_input.get("command", "")

    if not command:
        return None

    for risk in RISK_PATTERNS:
        if re.search(risk.pattern, command):
            if risk.severity == "block":
                return {
                    "deny": True,
                    "deny_message": f"Security risk: {risk.message}"
                }
            else:
                return {"warn": f"Security warning: {risk.message}"}

    return None
```

### Returning JSON results

Python function that returns structured results for context injection:

```toml
[[rules]]
id = "python-git-context"
description = "Inject git status context for commit operations"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "git commit"
'''
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.git:get_commit_context"
timeout_ms = 5000
```

Python implementation:

```python
"""Git context helpers for hooks."""

import subprocess
from pathlib import Path


def get_commit_context(context):
    """Get git context to inject before commit.

    Args:
        context: HookContext from the hook system.

    Returns:
        Dict with inject key containing helpful context.
    """
    cwd = context.hook_input.cwd

    try:
        # Get staged files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5
        )
        staged_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        # Get branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5
        )
        branch = result.stdout.strip()

        # Build context message
        context_msg = f"""Git commit context:
- Branch: {branch}
- Staged files ({len(staged_files)}): {', '.join(staged_files[:5])}{'...' if len(staged_files) > 5 else ''}
- Remember: Use conventional commits (feat:, fix:, docs:, etc.)"""

        return {"inject": context_msg}

    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
```

### Error handling patterns

Robust Python function with comprehensive error handling:

```toml
[[rules]]
id = "python-api-validator"
description = "Validate API calls against schema"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "curl.*api\\."
'''
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.api:validate_api_call"
timeout_ms = 10000
```

Python implementation with error handling:

```python
"""API validation for hook commands."""

import logging
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Allowed API endpoints
ALLOWED_HOSTS = {
    "api.github.com",
    "api.openai.com",
    "api.anthropic.com",
}

# Blocked patterns in URLs
BLOCKED_PATTERNS = [
    r"/admin/",
    r"/internal/",
    r"api_key=",
    r"secret=",
]


def validate_api_call(context):
    """Validate API calls for security.

    Args:
        context: HookContext from the hook system.

    Returns:
        Dict with deny/warn, or None if valid.
    """
    try:
        tool_input = context.hook_input.tool_input
        command = tool_input.get("command", "")

        # Extract URL from curl command
        url_match = re.search(r'curl\s+(?:-[a-zA-Z]+\s+)*["\']?(https?://[^\s"\']+)', command)
        if not url_match:
            # No URL found, allow (fail-open)
            return None

        url = url_match.group(1)

        try:
            parsed = urlparse(url)
        except ValueError as e:
            logger.warning(f"Failed to parse URL {url}: {e}")
            return {"warn": f"Could not parse URL: {url}"}

        # Check allowed hosts
        if parsed.hostname and parsed.hostname not in ALLOWED_HOSTS:
            return {
                "warn": f"API call to unrecognized host: {parsed.hostname}"
            }

        # Check blocked patterns
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return {
                    "deny": True,
                    "deny_message": f"API call contains blocked pattern in URL"
                }

        return None

    except Exception as e:
        # Fail-open: log error but don't block
        logger.exception(f"Error in validate_api_call: {e}")
        return None
```

### Complex validation logic

Multi-step validation with state tracking:

```toml
[[rules]]
id = "python-rate-limiter"
description = "Rate limit expensive operations"
events = ["pre_tool_use"]
priority = "high"
condition = '''
tool_name == "Bash" and tool_input.command =~~ "npm publish|cargo publish|twine upload"
'''
result = "ok"

[[rules.actions]]
type = "python"
entrypoint = "my_hooks.ratelimit:check_publish_rate"
timeout_ms = 5000
```

Python implementation with state:

```python
"""Rate limiting for hook operations."""

import json
import time
from pathlib import Path


# Rate limit: max 3 publishes per hour
MAX_PUBLISHES = 3
WINDOW_SECONDS = 3600


def check_publish_rate(context):
    """Check rate limit for publish operations.

    Uses a simple file-based rate limiter. In production,
    consider using the OAPS session/project state stores.

    Args:
        context: HookContext from the hook system.

    Returns:
        Dict with deny if rate limited, None otherwise.
    """
    state_file = Path(context.oaps_dir) / ".publish_rate_limit.json"
    now = time.time()

    # Load existing state
    timestamps = []
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text())
            timestamps = data.get("timestamps", [])
        except (json.JSONDecodeError, OSError):
            timestamps = []

    # Filter to window
    timestamps = [t for t in timestamps if now - t < WINDOW_SECONDS]

    # Check limit
    if len(timestamps) >= MAX_PUBLISHES:
        oldest = min(timestamps)
        wait_time = int(WINDOW_SECONDS - (now - oldest))
        return {
            "deny": True,
            "deny_message": f"Rate limited: {MAX_PUBLISHES} publishes per hour. Try again in {wait_time}s."
        }

    # Record this attempt
    timestamps.append(now)
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"timestamps": timestamps}))
    except OSError:
        pass  # Fail-open on state write errors

    return None
```

### Transform action with Python

Use Python for complex input transformations:

```toml
[[rules]]
id = "python-npm-to-pnpm"
description = "Transform npm commands to pnpm"
events = ["pre_tool_use"]
priority = "medium"
condition = '''
tool_name == "Bash" and tool_input.command.starts_with("npm ")
'''
result = "ok"

[[rules.actions]]
type = "transform"
entrypoint = "my_hooks.transforms:npm_to_pnpm"
timeout_ms = 5000
```

Python transform implementation:

```python
"""Command transformers for hooks."""

import re


# npm to pnpm command mapping
NPM_PNPM_MAP = {
    "npm install": "pnpm install",
    "npm i": "pnpm add",
    "npm ci": "pnpm install --frozen-lockfile",
    "npm run": "pnpm run",
    "npm test": "pnpm test",
    "npm start": "pnpm start",
    "npm publish": "pnpm publish",
    "npm exec": "pnpm exec",
    "npm init": "pnpm init",
}


def npm_to_pnpm(context):
    """Transform npm commands to pnpm equivalents.

    Args:
        context: HookContext from the hook system.

    Returns:
        Dict with transform_input containing modified command.
    """
    tool_input = context.hook_input.tool_input
    command = tool_input.get("command", "")

    if not command.startswith("npm "):
        return None

    new_command = command

    # Apply mappings
    for npm_cmd, pnpm_cmd in NPM_PNPM_MAP.items():
        if command.startswith(npm_cmd):
            new_command = pnpm_cmd + command[len(npm_cmd):]
            break

    # Handle npm install <package> -> pnpm add <package>
    install_match = re.match(r"npm\s+(?:install|i)\s+(\S+)", command)
    if install_match:
        package = install_match.group(1)
        if not package.startswith("-"):
            rest = command[install_match.end():]
            new_command = f"pnpm add {package}{rest}"

    if new_command != command:
        return {"transform_input": {"command": new_command}}

    return None
```
