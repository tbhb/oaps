---
name: dataclass-patterns
title: Dataclass patterns standard
description: Frozen dataclasses, slots optimization, validation in __post_init__, value objects. Load when designing data structures.
commands:
  uv run basedpyright: Type check dataclass definitions
  uv run pytest: Test dataclass behavior and validation
principles:
  - '**Always** use frozen{% if tool_versions.python | float >= 3.10 %} and slots{% endif %} for immutability{% if tool_versions.python | float >= 3.10 %} and memory efficiency{% endif %}'
  - Immutability prevents accidental mutation and enables hashability
  - '{% if tool_versions.python | float >= 3.10 %}Memory efficiency through slots reduces overhead by ~40%{% endif %}'
  - Validation **should** occur in __post_init__
  - Use value objects for domain primitives
best_practices:
  - '**Use frozen=True**: Enable immutability, hashability, and thread-safety'
  - '{% if tool_versions.python | float >= 3.10 %}**Use slots=True**: Reduce memory overhead by ~40% and enable faster attribute access{% endif %}'
  - '**Use object.__setattr__**: Required in __post_init__ for frozen dataclasses'
  - '**Use field(default_factory=...)**: Prevent shared mutable defaults'
  - '**Use order=True**: Enable comparison and ordering when needed'
  - '**Create value objects**: Add validation for domain primitives'
  - '**Avoid dataclasses for**: Complex initialization, mutable state with invariants, or polymorphic behavior'
checklist:
  - frozen=True for immutability
  - '{% if tool_versions.python | float >= 3.10 %}slots=True for memory efficiency{% endif %}'
  - Validation in __post_init__
  - Default factories for mutable defaults
  - Value objects for domain primitives
references:
  https://docs.python.org/3/library/dataclasses.html: dataclasses module
  https://peps.python.org/pep-0681/: PEP 681 - Data Class Transforms
  https://docs.python.org/3/whatsnew/{{ tool_versions.python }}.html: Python {{ tool_versions.python }} what's new
---

## Default configuration (Python {{ tool_versions.python }}+)

**Always** use frozen{% if tool_versions.python | float >= 3.10 %} and slots{% endif %}:

```python
from dataclasses import dataclass

@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class Point:
    """Immutable point{% if tool_versions.python | float >= 3.10 %} with memory efficiency{% endif %}."""
    x: float
    y: float
```

## Why frozen?

- **Immutability**: Prevents accidental mutation
- **Hashable**: Can be used in sets and dict keys
- **Thread-safe**: No synchronization needed

```python
@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class Config:
    name: str
    value: int

# Can use as dict key
cache: dict[Config, Result] = {}
```

{% if tool_versions.python | float >= 3.10 %}

## Why slots?

- **Memory efficiency**: ~40% less memory per instance
- **Faster attribute access**: Slight performance improvement
- **No **dict****: Prevents dynamic attribute assignment
  {% endif %}

## Validation with **post_init**

```python
from dataclasses import dataclass

@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class User:
    name: str
    age: int

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Name cannot be empty")
        if self.age < 0:
            raise ValueError("Age must be non-negative")
```

For frozen dataclasses, use object.**setattr**:

```python
@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class NormalizedString:
    value: str

    def __post_init__(self) -> None:
        # **Must** use object.__setattr__ for frozen dataclass
        object.__setattr__(self, "value", self.value.strip().lower())
```

## Default values and factories

```python
from dataclasses import dataclass, field

@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class Request:
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0
```

## Inheritance

```python
@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class Entity:
    id: str

@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class User(Entity):
    name: str
    email: str
```

## Value objects

For domain primitives, create value objects:

```python
@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %})
class EmailAddress:
    """Value object for validated email addresses."""
    value: str

    def __post_init__(self) -> None:
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

    def __str__(self) -> str:
        return self.value
```

## Comparison and ordering

```python
from dataclasses import dataclass

@dataclass(frozen=True{% if tool_versions.python | float >= 3.10 %}, slots=True{% endif %}, order=True)
class Version:
    major: int
    minor: int
    patch: int

# Now supports <, >, <=, >=
v1 = Version(1, 0, 0)
v2 = Version(2, 0, 0)
assert v1 < v2
```

## When **NOT** to use dataclasses

- **Complex initialization**: Use regular class with **init**
- **Mutable state with invariants**: Use class with property setters
- **Polymorphic behavior**: Consider Protocol or ABC
