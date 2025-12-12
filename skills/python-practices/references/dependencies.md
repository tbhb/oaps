---
name: dependencies
title: Dependencies standard
description: Common dependency choices, when to use each, standard library first philosophy. Load when adding or evaluating dependencies.
commands:
  uv add <package>: Add runtime dependency
  uv add --dev <package>: Add development dependency
  uv remove <package>: Remove dependency
  uv sync: Sync dependencies from lock file
  uv lock: Update lock file
  uv pip list: List installed packages
  uv pip show <package>: Show package details
  uv tree: Show dependency tree
principles:
  - '**Standard library first, dependencies last**'
  - '**Always** evaluate stdlib before considering third-party'
  - '**Justify every dependency**'
  - '**Prefer well-maintained, typed packages**'
best_practices:
  - '**Standard library first**: Check if standard library has the functionality before adding dependencies'
  - '**Justify dependencies**: Dependencies add maintenance burden - ensure the cost is worth it'
  - '**Verify maintenance**: Check recent commits and open issues to verify maintenance status'
  - '**Prefer typed packages**: Prefer packages with type hints for better type safety'
  - '**Review transitive dependencies**: Review transitive dependencies to avoid bloat'
  - '**Use dependency groups**: Use appropriate dependency groups (runtime vs dev vs optional)'
  - '**Pin minimum versions**: Pin minimum versions for compatibility'
checklist:
  - '**Stdlib alternatives considered**'
  - '**Dependency is well-maintained**'
  - '**Dependency has type hints**'
  - '**Minimal transitive dependencies**'
  - '**Added to correct group** (runtime vs dev)'
references:
  https://docs.astral.sh/uv/: uv package manager
  https://packaging.python.org/en/latest/specifications/pyproject-toml/: pyproject.toml specification
---

## Core philosophy

**Standard library first, dependencies last.**

1. **Always** evaluate stdlib before considering third-party
1. **Justify every dependency**
1. **Prefer well-maintained, typed packages**

## Runtime dependencies

### Type system

| Package           | Use for                                        |
| ----------------- | ---------------------------------------------- |
| typing-extensions | Modern typing features (TypeIs, ReadOnly, Doc) |
| annotated-types   | Metadata types for validation                  |

### Data handling

| Package  | Use for                              |
| -------- | ------------------------------------ |
| pydantic | Data validation, settings management |
| orjson   | Fast JSON serialization              |

### CLI and output

| Package   | Use for                            |
| --------- | ---------------------------------- |
| cyclopts  | CLI argument parsing               |
| rich      | Terminal formatting, progress bars |
| structlog | Structured logging                 |

### Date/time

| Package  | Use for                          |
| -------- | -------------------------------- |
| pendulum | Timezone-aware datetime handling |

## Development dependencies

### Testing

| Package     | Version | Use for                             |
| ----------- | ------- | ----------------------------------- |
| pytest      | >= 9.0  | Test framework (subtests, strict)   |
| pytest-cov  | >= 7.0  | Coverage reporting                  |
| pytest-mock | >= 3.15 | Mocking support                     |
| hypothesis  | >= 6.0  | Property-based testing              |
| pyfakefs    | >= 5.10 | Filesystem isolation                |

### Code quality

| Package      | Use for                |
| ------------ | ---------------------- |
| basedpyright | Type checking          |
| ruff         | Linting and formatting |
| codespell    | Spell checking         |
| yamllint     | YAML linting           |

### Performance

| Package          | Use for          |
| ---------------- | ---------------- |
| pytest-benchmark | Benchmarking     |
| py-spy           | CPU profiling    |
| memray           | Memory profiling |

### Mutation testing

| Package    | Use for          |
| ---------- | ---------------- |
| cosmic-ray | Mutation testing |

## When to add a dependency

Ask these questions:

1. **Can stdlib do this?** - **ALWAYS** check if standard library has the functionality
1. **Is it worth the cost?** - Dependencies add maintenance burden
1. **Is it maintained?** - **MUST** check recent commits, open issues
1. **Is it typed?** - **SHOULD** prefer packages with type hints
1. **What's the dependency tree?** - **MUST** check transitive dependencies

## Adding dependencies

```bash
# Runtime dependency
uv add pydantic

# Dev dependency
uv add --dev pytest

# Optional dependency group
uv add --group docs mkdocs
```

## pyproject.toml structure

```toml
[project]
dependencies = [
    "typing-extensions>=4.8",
    "pydantic>=2.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0",
    "basedpyright>=1.0",
    "ruff>=0.1",
]
docs = [
    "mkdocs>=1.5",
]
```
