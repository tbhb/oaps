---
name: code-organization
title: Code organization standard
description: Module structure, private modules, public API exports, class member ordering. Load when organizing code or designing module structure.
commands:
  tree <path>: View directory structure
  ls <path>: List directory contents
  uv run ruff check .: Verify import organization
principles:
  - '**Use leading underscore**: For implementation details and private modules'
  - '**Export public API**: Through __init__.py with explicit __all__'
  - '**Organize class members**: In a consistent, predictable order'
  - '**Separate imports**: Standard library, third-party, and local imports'
  - '**Prefer packages**: Over deep module nesting'
best_practices:
  - '**Group related modules**: In packages with __init__.py'
  - '**Define __all__**: For public modules to control exports'
  - '**Order class members**: Constants, lifecycle, magic methods, public interface, internals'
  - '**Place public properties first**: Before public methods'
  - '**Keep private/protected methods**: At the bottom of classes'
  - '**Follow isort/ruff conventions**: For import ordering'
  - '**Avoid deep package nesting**: That obscures intent'
checklist:
  - Private modules use leading underscore
  - Public API exported through __init__.py
  - __all__ defined for public modules
  - Class members ordered correctly
  - Imports organized by category
references:
  https://docs.python.org/3/tutorial/modules.html: Python modules tutorial
  https://peps.python.org/pep-0008/: PEP 8 - Style Guide for Python Code
---

## Module structure

```text
src/package/
├── __init__.py      # Public API exports
├── _internal.py     # Private module (leading underscore)
├── _utils.py        # Private utilities
├── models.py        # Public module
└── subpackage/
    ├── __init__.py
    └── _impl.py
```

## Private modules

Use leading underscore for implementation details:

```python
# src/package/_internal.py (private)
def _helper_function(): ...


# src/package/__init__.py (public API)
from ._internal import PublicClass

__all__ = ["PublicClass"]
```

## Public API exports

Export public API through `__init__.py`:

```python
# src/package/__init__.py
from .models import User, Config
from ._internal import process_data

__all__ = [
    "Config",
    "User",
    "process_data",
]
```

## Class member ordering

**MANDATORY** ordering:

```python
class Processor:
    # 1. Class State: Constants and class attributes
    DEFAULT_CONFIG = "default"
    RESERVED_NAMES = frozenset(["__init__", "__new__"])

    # 2. Lifecycle: __init__ and __new__
    def __init__(self, config: Config) -> None:
        self._config = config
        self._state = ProcessorState()

    # 3. Magic Methods: __repr__, __str__, __len__, etc.
    def __repr__(self) -> str:
        return f"Processor(config={self._config!r})"

    # 4. Public Interface: Properties first, then public methods
    @property
    def name(self) -> str:
        return self._config.get("name", self.DEFAULT_CONFIG)

    def process(self, data: Sequence[str]) -> Result:
        """Process data."""
        return self._process_impl(list(data))

    # 5. Internals: Private/protected methods at bottom
    def _process_impl(self, data: list[str]) -> Result: ...
```

## Import organization

Follow isort/ruff conventions:

```python
# 1. Standard library imports
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

# 2. Third-party imports
from typing_extensions import Doc, ReadOnly, TypeIs

# 3. Local imports
from package._module import Module
from package.validation import Validator
```

## Package vs module

- **Package**: Directory with `__init__.py`, groups related modules
- **Module**: Single `.py` file

```python
# Good: clear package structure
from myapp.auth import authenticate
from myapp.models import User

# Avoid: deep nesting
from myapp.core.services.auth.handlers import authenticate
```
