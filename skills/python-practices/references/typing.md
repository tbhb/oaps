---
name: typing
title: Typing standard
description: Type hints, basedpyright configuration, TypeIs, ReadOnly, Protocols. Load when working with type annotations or resolving type errors.
commands:
  uv run basedpyright: Type check code - must pass with zero errors and zero warnings
  uv run basedpyright <path>: Type check specific file or directory
principles:
  - Comprehensive type hints for all functions, methods, and class attributes
  - Zero tolerance for type errors and warnings
  - No suppressions without explicit user approval
  - '**NEVER** use from __future__ import annotations'
  - '**ALWAYS** use modern Python {{ tool_versions.python }}+ typing features'
best_practices:
  - '**Use TYPE_CHECKING blocks**: Import types only needed for hints inside TYPE_CHECKING blocks'
  - '**Use string literals**: Use string literals for forward references'
  - '{% if tool_versions.python | float >= 3.12 %}**Use PEP 695 syntax**: Use PEP 695 type parameter syntax for generics{% else %}**Use TypeVar**: Use TypeVar for generic type parameters{% endif %}'
  - '**Prefer explicit None**: Use `T | None` instead of `Optional[T]`'
  - '**Use collections.abc for parameters**: Use Sequence, Mapping for more flexible parameters'
  - '**Use concrete types for returns**: Use list, dict for return values'
  - '**Use TypeIs**: Use TypeIs for type narrowing'
  - '**Use ReadOnly**: Use ReadOnly for immutable TypedDict fields'
  - '**Use Protocols**: Use Protocols for structural typing'
  - '**Use @overload**: Use @overload when return type depends on input'
checklist:
  - All functions have return type annotations
  - All parameters have type annotations
  - '**NEVER** use from __future__ import annotations'
  - TYPE_CHECKING used for import-only types
  - basedpyright passes with zero errors/warnings
references:
  https://docs.basedpyright.com/: basedpyright type checker documentation
  https://typing-extensions.readthedocs.io/en/latest/: typing-extensions library documentation
  https://peps.python.org/pep-0695/: PEP 695 - Type Parameter Syntax
  https://docs.python.org/3/whatsnew/{{ tool_versions.python }}.html: Python {{ tool_versions.python }} what's new
---

## Critical rule

**NEVER use `from __future__ import annotations`**

This import (PEP 563) converts annotations to strings at runtime, breaking runtime type inspection. Instead use:

- `TYPE_CHECKING` blocks for import-only types
- String literals (`"ClassName"`) for forward references
- PEP 695 type parameter syntax for generics

## Type checker configuration

```toml
[tool.basedpyright]
typeCheckingMode = "strict"
pythonVersion = "{{ tool_versions.python }}"
reportImportCycles = "error"
```

## Modern typing patterns ({{ tool_versions.python }}+)

### TypeIs for type narrowing

```python
from typing_extensions import TypeIs


def is_string_list(value: list[object]) -> TypeIs[list[str]]:
    """Narrow list type to list[str]."""
    return all(isinstance(item, str) for item in value)


def process(items: list[object]) -> None:
    if is_string_list(items):
        # items is now list[str]
        for item in items:
            print(item.upper())
```

### ReadOnly for immutable typed dicts

```python
from typing_extensions import ReadOnly, TypedDict


class Config(TypedDict):
    """Configuration with immutable fields."""

    name: ReadOnly[str]
    options: ReadOnly[list[str]]
```

### Protocols for structural typing

```python
from typing import Protocol


class Renderable(Protocol):
    """Protocol for objects that can render to string."""

    def render(self) -> str: ...


def display(item: Renderable) -> None:
    print(item.render())
```

### TYPE_CHECKING for imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from .models import User


def load_user(path: "Path") -> "User": ...
```

## Function overloads

Use `@overload` when return type depends on input:

```python
from typing import overload


@overload
def get_item(index: int) -> str: ...
@overload
def get_item(index: slice) -> list[str]: ...
def get_item(index: int | slice) -> str | list[str]: ...
```

## Common patterns

### Optional vs Union

```python
# Preferred: explicit None
def find(name: str) -> User | None: ...


# Avoid: Optional is less clear
def find(name: str) -> Optional[User]: ...
```

### Collection types

```python
# Use collections.abc for parameters (more flexible)
from collections.abc import Sequence, Mapping


def process(items: Sequence[str]) -> None: ...


# Use concrete types for return values
def get_items() -> list[str]: ...
```
