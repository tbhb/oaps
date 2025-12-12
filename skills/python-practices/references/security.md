---
name: security
title: Security standard
description: Input validation, path traversal prevention, command injection prevention, sensitive data handling. Load when handling user input or external data.
commands:
  uv run ruff check . --select S: Run security-focused linting (bandit rules)
  uv run pytest: Run tests including security test cases
principles:
  - '**Validate all user input**: Validate all user input before use'
  - '**Prevent path traversal**: Prevent path traversal attacks by resolving and validating paths'
  - '**Never use shell=True**: **Never** execute shell commands with user input using shell=True'
  - '**Use parameterized queries**: Use parameterized queries to prevent SQL injection'
  - '**Never log sensitive data**: **Never** log or expose sensitive data in logs or representations'
  - '**Load secrets from environment**: Load secrets from environment variables, **never** hardcode'
  - '**Set restrictive permissions**: Set restrictive file permissions for sensitive files'
best_practices:
  - '**Validate input format**: Use regex patterns to validate input format and length'
  - '**Resolve and verify paths**: Resolve paths to absolute and verify they remain under base directory'
  - '**Use argument lists**: Use subprocess with argument lists instead of shell strings'
  - '**Quote shell input**: Use shlex.quote when shell execution is unavoidable'
  - '**Exclude sensitive fields**: Exclude sensitive fields from __repr__ and logging'
  - '**Require environment variables**: Raise errors when required environment variables are missing'
  - '**Owner-only permissions**: Set file permissions to owner-only (600) for sensitive files'
checklist:
  - '**All user input validated**: All user input validated before use'
  - '**Paths resolved and checked**: Paths resolved and checked against base directory'
  - '**No shell=True with user input**: No shell=True with user input'
  - '**SQL queries parameterized**: SQL queries use parameterization'
  - '**Sensitive data excluded**: Sensitive data excluded from logs/repr'
  - '**Secrets from environment**: Secrets loaded from environment'
references:
  https://cheatsheetseries.owasp.org/cheatsheets/Python_Security_Cheat_Sheet.html: OWASP Python Security Cheat Sheet
  https://bandit.readthedocs.io/en/latest/: Bandit docs
---

## Input validation

**Always** validate and sanitize user input:

```python
import re


def validate_username(username: str) -> str:
    """Validate and sanitize username."""
    if not username:
        raise ValueError("Username cannot be empty")
    if len(username) > 50:
        raise ValueError("Username too long")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValueError("Username contains invalid characters")
    return username
```

## Path traversal prevention

**Always** resolve and validate paths:

```python
from pathlib import Path


def safe_path_resolution(user_path: str, base: Path) -> Path:
    """Safely resolve paths to prevent traversal."""
    # Resolve to absolute path
    path = (base / user_path).resolve()

    # Verify it's still under base directory
    if not path.is_relative_to(base):
        raise ValueError("Path traversal detected")

    return path


# Usage
base_dir = Path("/app/data")
user_file = safe_path_resolution(user_input, base_dir)
```

## Command injection prevention

**NEVER** use shell=True with user input:

```python
import subprocess
import shlex

# DANGEROUS - **NEVER** do this
# subprocess.run(f"echo {user_input}", shell=True)


# Safe - use list of arguments
def run_command(filename: str) -> str:
    """Run command safely without shell injection."""
    # Validate input
    if not filename.isalnum():
        raise ValueError("Invalid filename")

    result = subprocess.run(
        ["cat", filename],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# If shell is needed, use shlex.quote
def safe_shell_command(user_input: str) -> str:
    """Safely quote input for shell use."""
    return shlex.quote(user_input)
```

## SQL injection prevention

Use parameterized queries:

```python
# DANGEROUS - SQL injection
# cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# Safe - parameterized query
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

## Sensitive data handling

**Never** log or expose sensitive data:

```python
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class User:
    id: str
    email: str
    password_hash: str

    def __repr__(self) -> str:
        # Exclude sensitive fields from repr
        return f"User(id={self.id!r}, email={self.email!r})"


def authenticate(email: str, password: str) -> User | None:
    # Log without sensitive data
    logger.info("Authentication attempt for email: %s", email)
    # **NEVER**: logger.info("Auth attempt: %s / %s", email, password)
    ...
```

## Environment variables for secrets

```python
import os


def get_api_key() -> str:
    """Get API key from environment."""
    key = os.environ.get("API_KEY")
    if not key:
        raise ValueError("API_KEY environment variable not set")
    return key


# **NEVER** hardcode secrets
# API_KEY = "sk-12345..."  # DANGEROUS
```

## File permissions

```python
from pathlib import Path
import stat


def create_secure_file(path: Path, content: str) -> None:
    """Create file with restricted permissions."""
    path.write_text(content)
    # Set read/write for owner only (600)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
```
