---
name: code-style
title: Code style standard
description: Import organization, pattern matching, modern Python features, naming conventions. Load when writing new code or reviewing style.
commands:
  uv run ruff check .: Lint code for style issues
  uv run ruff check --fix .: Lint and auto-fix issues
  uv run ruff format .: Format code
  uv run ruff format --check .: Check formatting without changing files
  just format: Format code via task runner
principles:
  - '**ALWAYS** use modern Python {{ tool_versions.python }}+ features'
  - '{% if tool_versions.python | float > 3.12 %}**MUST** use `type` statement for type aliases{% endif %}'
  - '**MUST** follow PEP 636 pattern matching for complex conditionals'
  - '**MUST** follow PEP 695 type parameter syntax for generics'
  - '**ALWAYS** use | syntax for type unions instead of Union'
best_practices:
  - '**Use f-strings**: Prefer f-strings for string formatting over .format() or %'
  - '**Use pathlib**: Use pathlib for all path handling instead of os.path'
  - '**Prefer comprehensions**: Use comprehensions over map/filter for transformations'
  - '**Use context managers**: Always use context managers for resource management'
  - '**Google-style docstrings**: Required for all public APIs'
  - '**Naming conventions**: lowercase_underscore for modules/functions, PascalCase for classes'
checklist:
  - Pattern matching for complex conditionals
  - '`|` syntax for unions'
  - f-strings for formatting
  - pathlib for path handling
  - Google-style docstrings for public APIs
references:
  https://docs.python.org/3/whatsnew/{{ tool_versions.python }}.html: Python {{ tool_versions.python }} what's new
  https://peps.python.org/pep-0636/: PEP 636 - Structural Pattern Matching
  https://peps.python.org/pep-0695/: PEP 695 - Type Parameter Syntax
---

## Modern Python features ({{ tool_versions.python }}+)

### Pattern matching

```python
match argument:
    case {"type": "option", "name": str(name)}:
        return process_option(name)
    case {"type": "value", "data": list(data)}:
        return process_value(data)
    case _:
        raise ValueError(f"Unknown argument: {argument}")
```

### Union syntax

```python
# Use | instead of Union
def process(value: str | int | None) -> str: ...


# Not
def process(value: Union[str, int, None]) -> str: ...
```

### Generic syntax (PEP 695)

```python
# Python 3.12+ style
def first[T](items: list[T]) -> T | None:
    return items[0] if items else None


class Stack[T]:
    def __init__(self) -> None:
        self._items: list[T] = []
```

## Naming conventions

| Type     | Convention           | Example            |
| -------- | -------------------- | ------------------ |
| Module   | lowercase_underscore | `user_auth.py`     |
| Class    | PascalCase           | `UserManager`      |
| Function | lowercase_underscore | `get_user_by_id`   |
| Constant | UPPERCASE_UNDERSCORE | `MAX_RETRIES`      |
| Private  | leading underscore   | `_internal_helper` |

## String formatting

Use f-strings:

```python
# Good
message = f"User {name} created at {timestamp}"

# Avoid
message = "User {} created at {}".format(name, timestamp)
message = "User %s created at %s" % (name, timestamp)
```

## Comprehensions

Prefer comprehensions over map/filter:

```python
# Good
squares = [x**2 for x in numbers]
evens = [x for x in numbers if x % 2 == 0]

# Avoid
squares = list(map(lambda x: x**2, numbers))
evens = list(filter(lambda x: x % 2 == 0, numbers))
```

## Path handling

Use pathlib:

```python
from pathlib import Path

# Good
config_path = Path("config") / "settings.json"
if config_path.exists():
    content = config_path.read_text()

# Avoid
import os

config_path = os.path.join("config", "settings.json")
if os.path.exists(config_path):
    with open(config_path) as f:
        content = f.read()
```

## Context managers

Use context managers for resource management:

```python
# Good
with open("file.txt") as f:
    content = f.read()

# For multiple resources
with (
    open("input.txt") as infile,
    open("output.txt", "w") as outfile,
):
    outfile.write(infile.read())
```

## Docstrings

Use Google style:

```python
def process_data(items: list[str], limit: int = 10) -> dict[str, int]:
    """Process a list of items and return counts.

    Args:
        items: List of strings to process.
        limit: Maximum number of results.

    Returns:
        Dictionary mapping items to their counts.

    Raises:
        ValueError: If items is empty.
    """
```
