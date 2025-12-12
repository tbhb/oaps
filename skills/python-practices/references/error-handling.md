---
name: error-handling
title: Error handling standard
description: Exception hierarchy design, error messages, recovery strategies, logging vs raising. Load when designing error handling.
commands:
  uv run pytest: Run tests to verify error handling
  uv run basedpyright: Type check exception types
principles:
  - Create package base exception
  - Chain exceptions with from
  - '**Never** catch bare Exception'
  - Write actionable error messages
  - Use specific exception types
  - Recovery vs propagation is intentional
best_practices:
  - '**Create base exception**: Create a base exception class for your package'
  - '**Derive domain exceptions**: Derive domain-specific exceptions from base exception'
  - '**Include context**: Include context in exception init (e.g., field name for validation errors)'
  - '**Write actionable messages**: Write error messages that explain what went wrong and how to fix it'
  - "**Chain exceptions**: Always chain exceptions to preserve context using 'from'"
  - '**Catch for recovery**: Catch when you can recover or need to translate to domain-specific error'
  - '**Let propagate**: Let exceptions propagate when caller should decide how to handle'
  - '**Use context managers**: Use context managers for cleanup to ensure resources are released'
  - '**Log and continue**: Log and continue for partial success scenarios'
  - '**Raise for errors**: Raise when caller must handle the error'
  - '**Catch specific exceptions**: Catch specific exceptions, not bare Exception'
---

## Exception hierarchy

Create a base exception for your package:

```python
class AppError(Exception):
    """Base exception for application."""


class ValidationError(AppError):
    """Raised when validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class ConfigurationError(AppError):
    """Raised when configuration is invalid."""


class NotFoundError(AppError):
    """Raised when a resource is not found."""
```

## Error messages

Write actionable error messages:

```python
# Good: explains what went wrong and how to fix
raise ValidationError(
    f"Invalid email format: {email!r}. Email must contain '@' and a domain."
)

# Bad: vague message
raise ValidationError("Invalid email")
```

## Exception chaining

**Always** chain exceptions to preserve context:

```python
def load_config(path: Path) -> Config:
    try:
        content = path.read_text()
        return parse_config(content)
    except FileNotFoundError as e:
        raise ConfigurationError(f"Config file not found: {path}") from e
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in config file: {path}") from e
```

## When to catch vs raise

**Catch when:**

- You can recover from the error
- You need to translate to domain-specific error
- You need to log and re-raise

**Let propagate when:**

- Caller should decide how to handle
- Error indicates a bug (let it crash)

```python
# Recovery possible
def get_user_or_default(user_id: str) -> User:
    try:
        return fetch_user(user_id)
    except NotFoundError:
        return User.guest()


# Translation needed
def process_file(path: Path) -> Data:
    try:
        return parse(path.read_text())
    except FileNotFoundError as e:
        raise ProcessingError(f"Input file missing: {path}") from e
```

## Logging vs raising

```python
import logging

logger = logging.getLogger(__name__)


def process(items: list[str]) -> list[Result]:
    results = []
    for item in items:
        try:
            results.append(transform(item))
        except TransformError:
            # Log and continue - partial success acceptable
            logger.warning("Failed to transform item: %s", item)
    return results


def validate(data: Data) -> None:
    if not data.is_valid():
        # Raise - caller must handle
        raise ValidationError("Data validation failed")
```

## Context managers for cleanup

```python
from contextlib import contextmanager


@contextmanager
def managed_connection(url: str):
    conn = connect(url)
    try:
        yield conn
    except ConnectionError:
        logger.error("Connection failed: %s", url)
        raise
    finally:
        conn.close()
```

## **Never** catch bare Exception

```python
# Bad
try:
    process()
except Exception:
    pass

# Good - catch specific exceptions
try:
    process()
except (ValueError, TypeError) as e:
    handle_error(e)
```
