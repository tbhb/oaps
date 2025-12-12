---
name: testing
title: Testing standard
description: pytest configuration, property-based testing with Hypothesis, coverage requirements, test organization. Load when writing or debugging tests.
related:
  - testing-antipatterns
commands:
  uv run pytest: Run all tests
  uv run pytest -k <pattern>: Run tests matching pattern
  uv run pytest --cov: Run tests with coverage reporting
  uv run pytest -x: Stop on first failure
  uv run pytest --pdb: Drop into debugger on failure
  just test: Run tests via task runner
principles:
  - '**No docstrings on tests** - names should be self-explanatory'
  - '**Maintain >95% coverage**'
  - Test functions named test_<scenario>_<expected>
  - Organize tests by domain, not by file
best_practices:
  - '**Use descriptive names**: Test names should describe scenario and expected outcome'
  - '**Use property-based testing**: Apply Hypothesis for invariants and edge cases'
  - '**Use pyfakefs**: Mock filesystem in unit tests'
  - '**Use tmp_path**: Real filesystem in integration tests**'
  - '**Use pytest fixtures**: Share reusable test data across tests'
  - '**Use parametrization**: Test multiple cases with pytest.mark.parametrize'
  - '**Use subtests for runtime-discovered cases**: Prefer subtests over parametrize when parameters are determined during test execution (pytest 9.0+)'
  - '**Test exceptions**: Use pytest.raises with match parameter for error messages'
  - '**Type hint mocker**: Annotate mocker fixture as MockerFixture'
  - '**Configure pytest strictly**: Enable strict xfail and error on warnings'
checklist:
  - Tests organized by domain, not by file
  - No docstrings on test functions
  - Names describe scenario and expected outcome
  - '>95% coverage maintained'
  - Property tests for invariants
  - pyfakefs for filesystem isolation in unit tests
  - tmp_path for real filesystem in integration tests
references:
  https://docs.pytest.org/en/stable/: pytest documentation
  https://docs.pytest.org/en/stable/changelog.html: pytest changelog (9.x features)
  https://hypothesis.readthedocs.io/en/latest/: Hypothesis property-based testing
  https://pytest-pyfakefs.readthedocs.io/en/latest/: pyfakefs filesystem mocking
---

## Test organization

```text
tests/
├── unit/           # Isolated unit tests
│   ├── test_module.py
│   └── domain/
│       └── test_feature.py
├── integration/    # Integration tests
├── properties/     # Hypothesis property tests
└── benchmarks/     # Performance tests
```

## Naming conventions

- Test files: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<scenario>_<expected>`
- **NEVER add docstrings on tests** - names should be self-explanatory

```python
# Good
def test_parse_valid_json_returns_dict(): ...
def test_parse_invalid_json_raises_value_error(): ...


# Bad
def test_parse(): ...
def test_1(): ...
```

## Coverage requirements

- Maintain **>95% coverage**
- Run with: `just test-coverage` or `just test-coverage <pattern>`

## pytest configuration

```toml
[tool.pytest.ini_options]
addopts = [
  "--import-mode=importlib",
  "--tb",
  "short",
  "--ignore=tests/benchmarks",
]
pythonpath = ["src", "."]
filterwarnings = ["error"]
testpaths = ["tests"]
strict = true  # pytest 9.0+: enables strict_config, strict_markers, strict_xfail, strict_parametrization_ids
markers = [
  "benchmark: mark a test as a benchmark test.",
  "docexamples: mark a test as a documentation example test.",
  "integration: mark a test as an integration test.",
  "property: mark a test as a property test.",
  "unit: mark a test as a unit test.",
]
```

**Note:** pytest 9.0+ supports native TOML configuration via `[tool.pytest]` as an alternative to `[tool.pytest.ini_options]`. The legacy table remains compatible but cannot coexist with native TOML config.

## Unit test isolation

**ALWAYS use pyfakefs for filesystem tests, NEVER use tmp_path:**

```python
from pyfakefs.fake_filesystem_unittest import Patcher


def test_read_config_file():
    with Patcher() as patcher:
        patcher.fs.create_file("/config.json", contents='{"key": "value"}')
        result = read_config("/config.json")
        assert result == {"key": "value"}
```

## pytest-mock typing

```python
from unittest.mock import MagicMock
from pytest_mock import MockerFixture


def test_with_mock(mocker: MockerFixture) -> None:
    mock_func = mocker.patch("module.func")
    mock_func.return_value = "mocked"
    # ...
```

## Property-based testing with Hypothesis

```python
from hypothesis import given, strategies as st


@given(st.lists(st.integers()))
def test_sort_is_idempotent(items: list[int]) -> None:
    sorted_once = sorted(items)
    sorted_twice = sorted(sorted_once)
    assert sorted_once == sorted_twice


@given(st.text(min_size=1))
def test_strip_reduces_length(text: str) -> None:
    assert len(text.strip()) <= len(text)
```

## Common patterns

### Fixtures

```python
import pytest


@pytest.fixture
def sample_config() -> dict[str, str]:
    return {"name": "test", "value": "123"}


def test_process_config(sample_config: dict[str, str]) -> None:
    result = process(sample_config)
    assert result.name == "test"
```

### Parametrization

```python
import pytest


@pytest.mark.parametrize(
    "input,expected",
    [
        ("hello", "HELLO"),
        ("world", "WORLD"),
        ("", ""),
    ],
)
def test_uppercase(input: str, expected: str) -> None:
    assert input.upper() == expected
```

### Testing exceptions

```python
import pytest


def test_invalid_input_raises() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        process_value(-1)
```

## Subtests (pytest 9.0+)

Subtests allow testing multiple scenarios within a single test function when parameters are determined at runtime. Unlike `@pytest.mark.parametrize`, subtests are generated during test execution.

### Basic usage

```python
from pathlib import Path
import pytest


def test_all_config_files_valid(subtests: pytest.Subtests) -> None:
    for path in Path("configs").glob("*.toml"):
        with subtests.test(config=path.name):
            config = load_config(path)
            assert config.validate()
```

### When to use subtests vs parametrize

| Scenario | Use |
| -------- | --- |
| Parameters known at collection time | `@pytest.mark.parametrize` |
| Parameters discovered at runtime | `subtests` |
| Need separate test items in reports | `@pytest.mark.parametrize` |
| Testing dynamic/discovered data | `subtests` |

### Subtest reporting

- Default output shows single test result
- Verbose (`-v`) shows individual subtests as "SUBPASSED"/"SUBFAILED"
- Summary shows: "9 passed, 116 subtests passed"

### unittest.TestCase compatibility

pytest 9.0+ also supports `unittest.TestCase.subTest()`:

```python
import unittest


class TestFiles(unittest.TestCase):
    def test_all_valid(self) -> None:
        for name in ["a.txt", "b.txt"]:
            with self.subTest(file=name):
                self.assertTrue(validate(name))
```
