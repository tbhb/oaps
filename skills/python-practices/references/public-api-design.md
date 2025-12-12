---
name: public-api-design
title: Public API design standard
description: API ergonomics, method signatures, progressive disclosure, overloads, type safety. Load when designing public interfaces.
commands:
  uv run basedpyright: Type check API signatures and overloads
  uv run pytest: Test API behavior
principles:
  - "**Minimal surface area**: Expose only what's necessary"
  - '**Consistency**: Similar operations should have similar signatures'
  - '**Type safety**: APIs should be impossible to misuse with types'
  - '**Progressive disclosure**: Simple things simple, complex things possible'
  - '**Use modern Python {{ tool_versions.python }}+ features**'
best_practices:
  - "**Export public API through __all__**: Define __all__ in __init__.py to explicitly control what's exported"
  - '**Keep implementation details private**: Use underscore prefix for internal modules and helpers'
  - '**Use consistent parameter ordering**: Similar functions should have parameters in the same order'
  - '**Use NewType for distinct domain types**: Prevent confusion between conceptually different strings/ints'
  - '**Use overloads to specify return types**: Different return types based on arguments for better type safety'
  - '**Use default parameters for progressive disclosure**: Simple cases should work without configuration'
  - '**Use keyword-only arguments**: Force explicit naming with * separator for options'
  - '**Provide factory methods**: Offer classmethod constructors for complex initialization patterns'
  - '**Make error handling explicit**: Use return types or documented exceptions to indicate failures'
  - '{% if tool_versions.python | float >= 3.12 %}**Use PEP 695 generics**: Use type parameter syntax for generic classes and functions{% endif %}'
checklist:
  - '**Only necessary items in __all__**: Minimal public surface area'
  - '**Consistent parameter ordering**: Similar operations use same order'
  - '**Types prevent misuse**: NewType and overloads enforce correct usage'
  - '**Keyword-only for optional parameters**: Force explicit naming'
  - "**Simple cases don't require options**: Progressive disclosure via defaults"
  - '**Error handling is explicit**: Return types or documented exceptions'
references:
  https://peps.python.org/pep-0008/: PEP 8 - Style Guide
  https://semver.org/: Semantic Versioning specification
  https://docs.python.org/3/whatsnew/{{ tool_versions.python }}.html: Python {{ tool_versions.python }} what's new
---

## Minimal surface area

```python
# __init__.py - only export public API
from ._internal import (
    parse,
    format,
    Config,
)

__all__ = [
    "Config",
    "format",
    "parse",
]

# Keep implementation details private
# from ._internal import _helper  # **DO NOT** export
```

## Consistent signatures

```python
# Good: consistent parameter ordering
def read_file(path: Path, encoding: str = "utf-8") -> str: ...
def write_file(path: Path, content: str, encoding: str = "utf-8") -> None: ...


# Bad: inconsistent ordering
def read_file(path: Path, encoding: str = "utf-8") -> str: ...
def write_file(content: str, path: Path, encoding: str = "utf-8") -> None: ...
```

## Type-safe APIs

Use types to **prevent misuse**:

```python
from typing import NewType

# Create distinct types
UserId = NewType("UserId", str)
OrderId = NewType("OrderId", str)


def get_user(user_id: UserId) -> User: ...
def get_order(order_id: OrderId) -> Order: ...


# Prevents mixing up IDs
user = get_user(UserId("u123"))
# get_user(OrderId("o456"))  # Type error!
```

## Overloads for different return types

```python
from typing import overload


@overload
def fetch(url: str, *, json: Literal[True]) -> dict: ...
@overload
def fetch(url: str, *, json: Literal[False] = ...) -> str: ...
def fetch(url: str, *, json: bool = False) -> dict | str:
    response = requests.get(url)
    return response.json() if json else response.text
```

## Progressive disclosure

Simple cases **should be simple**:

```python
# Simple usage
result = parse("input.txt")

# Advanced usage with options
result = parse(
    "input.txt",
    encoding="utf-8",
    strict=True,
    on_error=ErrorHandler.SKIP,
)
```

Achieved with default parameters:

```python
def parse(
    path: str | Path,
    *,
    encoding: str = "utf-8",
    strict: bool = False,
    on_error: ErrorHandler = ErrorHandler.RAISE,
) -> ParseResult: ...
```

## Keyword-only arguments

Use `*` to force keyword arguments:

```python
def connect(
    host: str,
    port: int,
    *,  # Everything after is keyword-only
    timeout: float = 30.0,
    ssl: bool = True,
) -> Connection: ...


# Forces explicit naming
conn = connect("localhost", 8080, timeout=60.0, ssl=False)
# connect("localhost", 8080, 60.0, False)  # Error!
```

## Factory methods for complex construction

```python
class Config:
    def __init__(self, settings: dict[str, Any]) -> None:
        self._settings = settings

    @classmethod
    def from_file(cls, path: Path) -> Self:
        """Load config from file."""
        content = path.read_text()
        return cls(json.loads(content))

    @classmethod
    def from_env(cls) -> Self:
        """Load config from environment."""
        return cls(dict(os.environ))
```

## Error handling in APIs

Return types **should indicate** possible failures:

```python
# Option 1: Return None for not found
def find_user(user_id: str) -> User | None: ...

# Option 2: Raise specific exception
def get_user(user_id: str) -> User:
    """Get user by ID.

    Raises:
        UserNotFoundError: If user doesn't exist.
    """
    ...

# Option 3: Result type for complex errors
{% if tool_versions.python | float >= 3.12 %}@dataclass
class Result[T]:
    value: T | None
    error: Error | None{% else %}from typing import TypeVar, Generic

T = TypeVar("T")

@dataclass
class Result(Generic[T]):
    value: T | None
    error: Error | None{% endif %}
```
