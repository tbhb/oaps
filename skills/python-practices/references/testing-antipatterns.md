---
name: testing-antipatterns
title: Testing antipatterns
description: Unit testing anti-patterns that produce tests with little or no value. Load when writing or reviewing tests.
principles:
  - 'A valuable test **fails when the code is broken** and passes when correct'
  - 'Test **behavior**, not implementation'
  - 'Use **pre-calculated literal values** for expected results, not computed values'
  - 'Each test should be capable of failing - if it cannot fail, it has no value'
antipatterns:
  - 'Tautological tests that only verify Python assignment works'
  - 'Testing the mock instead of the code'
  - 'No meaningful assertions (just assert not None or isinstance)'
  - 'Mirroring implementation logic in test expected values'
  - 'Testing trivial/auto-generated code like plain dataclasses'
  - 'Blanket exception swallowing with try/except: pass'
  - 'Testing language/framework features instead of your code'
  - 'Asserting on incidental details like exact error messages'
  - 'Tests that structurally cannot fail'
  - 'Testing implementation instead of behavior'
  - 'Excessive setup with minimal verification'
  - 'Copy-paste tests instead of parametrize'
  - 'Misleading or vague test names'
  - 'Only testing happy paths, ignoring edge cases'
  - 'Time-dependent tests without time control'
  - 'Order-dependent tests with shared mutable state'
  - 'Verifying logging as the primary assertion'
checklist:
  - Ask "What bug would cause this test to fail?"
  - Assert on actual outcomes, not mocked return values
  - Use literal expected values, not computed ones
  - Test edge cases and error conditions, not just happy paths
  - Ensure each test can actually fail
  - Use parametrize instead of copy-paste tests
  - Name tests to describe scenario and expected outcome
---

## Tautological tests

A tautological test asserts exactly what it just set up, proving only that Python's basic mechanics work.

```python
# Bad - tests Python assignment, not your code
def test_user_name():
    user = User()
    user.name = "Alice"
    assert user.name == "Alice"


# Good - test that behavior is correct
def test_user_name_persists_after_save_load_cycle():
    user = User(name="Alice")
    user.save()
    loaded = User.load(user.id)
    assert loaded.name == "Alice"
```

## Testing the mock instead of the code

When you mock a dependency and then assert it returned what you configured it to return, you've only verified your test setup.

```python
# Bad - just testing the mock
def test_get_user(mocker: MockerFixture) -> None:
    mock_db = mocker.patch("app.database.get_user")
    mock_db.return_value = {"id": 1, "name": "Alice"}
    result = get_user(1)
    assert result == {"id": 1, "name": "Alice"}


# Good - test what code does with the mocked value
def test_get_user_formats_display_name(mocker: MockerFixture) -> None:
    mock_db = mocker.patch("app.database.get_user")
    mock_db.return_value = {"id": 1, "first": "Alice", "last": "Smith"}
    result = get_user(1)
    assert result.display_name == "Alice Smith"
```

## No meaningful assertions

Tests that call code but assert nothing substantive pass for almost any implementation.

```python
# Bad - passes whether function works, does nothing, or corrupts data
def test_process_data():
    result = process_data({"key": "value"})
    assert result is not None
    assert isinstance(result, dict)


# Good - assert on actual expected outcomes
def test_process_data_transforms_keys_to_uppercase():
    result = process_data({"key": "value"})
    assert result == {"KEY": "value"}
```

## Mirroring implementation logic

When your test calculates the expected result using the same algorithm as the code under test, bugs appear in both places simultaneously.

```python
# Bad - same formula in test and implementation
def test_calculate_discount():
    price, percentage = 100, 20
    expected = price * (1 - percentage / 100)  # Same formula!
    assert calculate_discount(price, percentage) == expected


# Good - use pre-calculated literal values
def test_calculate_discount_twenty_percent_off():
    assert calculate_discount(100, 20) == 80.0
```

## Testing trivial code

Auto-generated code, simple property access, and framework boilerplate don't benefit from testing.

```python
@dataclass
class User:
    name: str
    email: str


# Bad - tests that @dataclass works
def test_user_dataclass():
    user = User(name="Alice", email="alice@example.com")
    assert user.name == "Alice"
    assert user.email == "alice@example.com"


# Good - test custom logic like __post_init__ validation
@dataclass
class User:
    name: str
    email: str

    def __post_init__(self):
        if "@" not in self.email:
            raise ValueError("Invalid email")


def test_user_validates_email_format():
    with pytest.raises(ValueError, match="Invalid email"):
        User(name="Alice", email="invalid")
```

## Blanket exception swallowing

Wrapping test code in `try/except: pass` turns failures into silent passes. This test is literally incapable of failing.

```python
# Bad - incapable of failing
def test_data_processing():
    try:
        result = process_data(invalid_input)
        assert result["status"] == "success"
    except:
        pass


# Good - let exceptions propagate, use pytest.raises for expected ones
def test_data_processing_succeeds():
    result = process_data(valid_input)
    assert result["status"] == "success"


def test_data_processing_invalid_input_raises():
    with pytest.raises(ValidationError):
        process_data(invalid_input)
```

## Testing language or framework features

Verifying that Python's standard library or your framework behaves as documented wastes effort.

```python
# Bad - testing Python, not your code
def test_json_parsing():
    data = json.loads('{"key": "value"}')
    assert data == {"key": "value"}


# Good - test your code that uses these features
def test_config_loader_parses_json_file():
    with Patcher() as patcher:
        patcher.fs.create_file("/config.json", contents='{"debug": true}')
        config = ConfigLoader.load("/config.json")
        assert config.debug is True
```

## Asserting on incidental details

Testing exact error messages, log formatting, or internal structure couples tests to implementation rather than behavior.

```python
# Bad - breaks when error message is reworded
def test_validation_error():
    with pytest.raises(ValueError) as exc:
        validate_email("not-an-email")
    assert str(exc.value) == "Invalid email format: missing @ symbol"


# Good - assert on exception type and key info
def test_validation_error():
    with pytest.raises(ValueError, match="email"):
        validate_email("not-an-email")
```

## Tests that cannot fail

Various patterns make tests structurally incapable of failing.

```python
# Bad - conditional assertion
def test_conditional_assertion():
    result = get_result()
    if result:  # Assertion only runs conditionally
        assert result["status"] == "ok"


# Bad - self-fulfilling
def test_self_fulfilling():
    expected = my_function()  # Calling function to get "expected"
    actual = my_function()
    assert actual == expected  # Always passes unless non-deterministic


# Good - unconditional assertions with literal expected values
def test_result_status():
    result = get_result()
    assert result is not None
    assert result["status"] == "ok"
```

## Testing implementation instead of behavior

Tests that verify how code works internally rather than what it accomplishes break during refactoring.

```python
# Bad - testing exact SQL rather than outcome
def test_user_save(mocker: MockerFixture) -> None:
    mock_db = mocker.patch("app.db.execute")
    user = User(name="Alice")
    user.save()
    mock_db.assert_called_once_with(
        "INSERT INTO users (name) VALUES (?)",
        ("Alice",),
    )


# Good - test that saved user can be retrieved
def test_user_save_persists_data():
    user = User(name="Alice")
    user.save()
    loaded = User.get(user.id)
    assert loaded.name == "Alice"
```

## Copy-paste tests

Duplicated tests that differ only slightly create maintenance nightmares.

```python
# Bad - 15 nearly identical tests
def test_process_type_a():
    result = process({"type": "a", "value": 1})
    assert result["processed"] is True


def test_process_type_b():
    result = process({"type": "b", "value": 1})
    assert result["processed"] is True


# Good - use parametrize
@pytest.mark.parametrize("type_", ["a", "b", "c", "d", "e"])
def test_process_types(type_: str) -> None:
    result = process({"type": type_, "value": 1})
    assert result["processed"] is True
    assert result["type"] == type_
```

## Misleading test names

Test names that don't reflect what's actually being tested make failures confusing.

```python
# Bad - vague, unhelpful names
def test_user(): ...
def test_success(): ...
def test_bug_fix_123(): ...
def test_it_works(): ...


# Good - describe scenario and expected outcome
def test_user_with_expired_subscription_cannot_access_premium_content(): ...
def test_parse_valid_json_returns_dict(): ...
def test_empty_input_raises_validation_error(): ...
```

## Ignoring edge cases

Tests that only cover the obvious successful case miss where bugs actually hide.

```python
# Bad - only happy path
def test_divide():
    assert divide(10, 2) == 5


# Good - test edge cases where bugs lurk
@pytest.mark.parametrize(
    "a,b,expected",
    [
        (10, 2, 5),
        (-10, 2, -5),
        (0, 5, 0),
    ],
)
def test_divide(a: int, b: int, expected: int) -> None:
    assert divide(a, b) == expected


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
```

## Time-dependent tests without time control

Tests that depend on the current time are flaky and can fail unpredictably.

```python
# Bad - slow, flaky
def test_is_expired():
    token = Token(expires_at=datetime.now() + timedelta(seconds=1))
    assert not token.is_expired()
    time.sleep(2)
    assert token.is_expired()


# Good - use freezegun or time-machine
from freezegun import freeze_time


def test_is_expired():
    with freeze_time("2024-01-01 12:00:00"):
        token = Token(expires_at=datetime(2024, 1, 1, 12, 0, 30))
        assert not token.is_expired()

    with freeze_time("2024-01-01 12:01:00"):
        assert token.is_expired()
```

## Order-dependent tests

Tests that only pass when run in a specific order or share mutable state are fragile.

```python
# Bad - test_query depends on test_insert running first
class TestDatabase:
    def test_insert(self):
        db.insert({"id": 1, "name": "Alice"})

    def test_query(self):
        result = db.query(id=1)  # Depends on test_insert
        assert result["name"] == "Alice"


# Good - each test sets up its own state
class TestDatabase:
    def test_insert(self, db_fixture):
        db_fixture.insert({"id": 1, "name": "Alice"})
        assert db_fixture.exists(id=1)

    def test_query(self, db_fixture):
        db_fixture.insert({"id": 1, "name": "Alice"})
        result = db_fixture.query(id=1)
        assert result["name"] == "Alice"
```

## Verifying logging as the primary assertion

Using log output as the main verification mechanism makes tests fragile and often misses actual bugs.

```python
# Bad - logs don't prove correctness
def test_process_item(caplog):
    process_item(item)
    assert "Processing item" in caplog.text
    assert "Item processed successfully" in caplog.text


# Good - assert on actual outcomes
def test_process_item():
    result = process_item(item)
    assert result.status == "processed"
    assert result.output_path.exists()
```

## Summary

When reviewing tests, ask: **"What bug would cause this test to fail?"** If you can't think of one, or if the answer is "only if I break the test itself," the test has no value.

A valuable test:

- Fails when the code is broken
- Passes when the code is correct
- Tests behavior rather than implementation
- Makes failures easy to diagnose
