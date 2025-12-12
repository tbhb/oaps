---
name: tooling
title: Tooling standard
description: uv, basedpyright, ruff, pytest, just configuration and CLI invocations. Load when configuring tools or running quality checks.
required: true
commands:
  uv run python <script>: Run Python script - **ALWAYS** use uv run for Python execution
  uv run --isolated --python 3.11 python <script>: Run Python script with isolated environment and specific Python version
  "{% if 'basedpyright' in tool_versions %}uv run basedpyright{% endif %}": Type check code
  "{% if 'ruff' in tool_versions %}uv run ruff check .{% endif %}": Lint code
  "{% if 'ruff' in tool_versions %}uv run ruff format .{% endif %}": Format code
  "{% if 'pytest' in tool_versions %}uv run pytest{% endif %}": Run tests
  "{% if 'codespell' in tool_versions %}uv run codespell{% endif %}": Check spelling
  uv sync: Sync dependencies from lock file
  just lint: Run all linters
  just test: Run all tests
  just format: Format all code
  just lint && just test: Full quality check
principles:
  - '**Always** use uv run for Python execution'
  - '**Target Python {{ tool_versions.python }}** for all tools'
  - Type check with zero errors and warnings
  - '**Maintain** strict type checking mode'
  - Enable all linters by default, disable selectively
  - Format code automatically with tooling
  - Treat warnings as errors in tests
best_practices:
  - '**Always use uv run**: Use uv for all package management and Python execution'
  - '**Quality gates required**: Run quality gates before completing work'
  - '**Use just for workflows**: Use just for common development workflows'
  - '**Enable docstring formatting**: Enable docstring code formatting in ruff'
  - '**Use importlib mode**: Use pytest with import mode importlib'
  - '**Maintain coverage**: Maintain >95% test coverage'
  - '**Auto-fix when possible**: Auto-fix linting issues when possible'
  - '**Stop on first failure**: Stop tests on first failure during debugging'
checklist:
  - uv run used for all Python execution
  - basedpyright passes with zero errors/warnings
  - ruff check passes
  - pytest passes with >95% coverage
  - codespell passes
references:
  https://docs.astral.sh/ruff/: Ruff linter and formatter
  https://docs.astral.sh/uv/: uv package manager
  https://docs.basedpyright.com/: basedpyright type checker
  https://docs.python.org/3/whatsnew/{{ tool_versions.python }}.html: Python {{ tool_versions.python }} what's new
---

## Required tooling stack

| Tool         | Purpose                | Required    |
| ------------ | ---------------------- | ----------- |
| uv           | Package management     | Yes         |
| basedpyright | Type checking          | Yes         |
| ruff         | Linting and formatting | Yes         |
| pytest       | Testing                | Yes         |
| just         | Task runner            | Yes         |
| codespell    | Spell checking         | Yes         |
| hypothesis   | Property testing       | Recommended |
| cosmic-ray   | Mutation testing       | Optional    |

## Package management (uv)

**MANDATORY: ALWAYS use `uv run` for Python execution.**

```bash
# Sync dependencies
uv sync

# Add dependency
uv add <package>
uv add --dev <package>  # Dev dependency

# Remove dependency
uv remove <package>

# Run Python
uv run python script.py
uv run python -m module

# Run tools
uv run pytest
uv run ruff check .
uv run basedpyright
```

## Type checking (basedpyright)

Configuration:

```toml
[tool.basedpyright]
typeCheckingMode = "strict"
pythonVersion = "{{ tool_versions.python }}"
reportImportCycles = "error"
```

Invocation:

```bash
uv run basedpyright
uv run basedpyright src/  # Specific directory
```

## Linting and formatting (ruff)

Configuration:

```toml
[tool.ruff]
target-version = "py{{ tool_versions.python | replace('.', '') }}"

[tool.ruff.lint]
select = ["ALL"]
ignore = ["D", "TD003"]  # Customize as needed

[tool.ruff.format]
docstring-code-format = true
```

Invocation:

```bash
# Check
uv run ruff check .
uv run ruff check --fix .  # Auto-fix

# Format
uv run ruff format .
uv run ruff format --check .  # Check only
```

## Testing (pytest)

Configuration (pytest 9.0+):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--import-mode=importlib", "--tb", "short"]
filterwarnings = ["error"]
strict = true  # Enables strict_config, strict_markers, strict_xfail, strict_parametrization_ids
```

**Note:** pytest 9.0+ also supports native TOML via `[tool.pytest]` as an alternative to `[tool.pytest.ini_options]`.

Invocation:

```bash
uv run pytest
uv run pytest -k "test_name"  # Run specific test
uv run pytest --cov  # With coverage
uv run pytest -x  # Stop on first failure
```

## Task runner (just)

Common recipes:

```bash
just install    # Install dependencies
just test       # Run tests
just lint       # Run all linters
just format     # Format code
just clean      # Clean artifacts
just prek       # Pre-commit checks
```

## Quality gates

Before completing work, run:

```bash
# All at once
just lint && just test

# Or individually
uv run basedpyright        # Type checking
uv run ruff check .        # Linting
uv run pytest --cov        # Tests with coverage
```

## Spell checking

```bash
uv run codespell           # Check
uv run codespell -w        # Fix in-place
```
