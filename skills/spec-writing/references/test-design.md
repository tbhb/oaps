---
name: test-design
title: Test design
description: Deriving test cases from specifications, coverage strategies, acceptance test design, edge case identification. Load when designing test cases or validation strategies.
commands:
  uv run pytest: Run tests
  uv run pytest -k <pattern>: Run tests matching pattern
  uv run pytest --cov: Run with coverage
principles:
  - '**Trace to requirements**: Every test should link to a requirement'
  - '**Test behavior, not implementation**: Focus on observable outcomes'
  - '**Cover boundaries**: Edge cases reveal bugs'
  - '**Independent tests**: Each test should run in isolation'
best_practices:
  - '**Start with acceptance criteria**: Derive tests from spec, not code'
  - '**Use equivalence partitioning**: Group similar inputs, test representative values'
  - '**Apply boundary analysis**: Test at limits and just beyond'
  - '**Include negative tests**: Verify error handling works correctly'
  - '**Automate where valuable**: Prioritize tests that catch regressions'
checklist:
  - Each requirement has at least one test case
  - Happy path scenarios covered
  - Error conditions tested
  - Boundary values included
  - Test cases are traceable to requirements
references:
  https://docs.pytest.org/: pytest documentation
  https://hypothesis.readthedocs.io/: Hypothesis property-based testing
---

## Deriving tests from specifications

### Requirement-to-test mapping

For each requirement, identify test scenarios:

```markdown
## Requirement
**REQ-001**: The system shall validate email addresses before account creation.

## Derived test cases
| ID | Scenario | Input | Expected |
|----|----------|-------|----------|
| TC-001-01 | Valid email | user@example.com | Accepted |
| TC-001-02 | Missing @ | userexample.com | Rejected |
| TC-001-03 | Missing domain | user@ | Rejected |
| TC-001-04 | Multiple @ | user@@example.com | Rejected |
| TC-001-05 | Unicode domain | user@exämple.com | Accepted (IDN) |
```

### Acceptance criteria to tests

Convert Given-When-Then to test structure:

```gherkin
# Acceptance criterion
Given a user with valid credentials
When they submit the login form
Then they are redirected to the dashboard
  And a session cookie is set
```

```python
def test_successful_login_redirects_to_dashboard():
    # Given
    user = create_user(email="test@example.com", password="valid123")

    # When
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "valid123"}
    )

    # Then
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    assert "session" in response.cookies
```

## Test coverage strategies

### Coverage levels

| Level           | Focus                          | When to use           |
| --------------- | ------------------------------ | --------------------- |
| Happy path      | Normal, expected flow          | Always                |
| Error handling  | Invalid inputs, failures       | Always                |
| Boundary values | Limits, edge cases             | High-risk areas       |
| Security        | Auth, authorization, injection | Security-critical     |
| Performance     | Load, stress, timing           | Performance-sensitive |

### Prioritization matrix

| Risk | Frequency | Priority          |
| ---- | --------- | ----------------- |
| High | High      | P0 - Test first   |
| High | Low       | P1 - Must test    |
| Low  | High      | P2 - Should test  |
| Low  | Low       | P3 - Nice to have |

## Test case design techniques

### Equivalence partitioning

Group inputs into classes that should behave identically:

```markdown
## Input: Age field (valid range: 0-120)

| Partition | Example values | Expected |
|-----------|----------------|----------|
| Below minimum | -1, -100 | Invalid |
| At minimum | 0 | Valid |
| Normal range | 25, 50, 75 | Valid |
| At maximum | 120 | Valid |
| Above maximum | 121, 999 | Invalid |
| Non-numeric | "abc", null | Invalid |
```

### Boundary value analysis

Test at and around boundaries:

```markdown
## Field: Username (3-20 characters)

| Test point | Value | Expected |
|------------|-------|----------|
| Below min | "ab" (2 chars) | Invalid |
| At min | "abc" (3 chars) | Valid |
| Above min | "abcd" (4 chars) | Valid |
| Below max | 19 characters | Valid |
| At max | 20 characters | Valid |
| Above max | 21 characters | Invalid |
```

### Decision tables

For complex logic with multiple conditions:

```markdown
## Rule: Free shipping eligibility

| Condition | R1 | R2 | R3 | R4 |
|-----------|----|----|----|----|
| Order > $50 | Y | Y | N | N |
| Premium member | Y | N | Y | N |
| **Free shipping** | Y | Y | Y | N |
```

## Test case template

See the **Test case template** for the complete structure including title, requirement traceability, priority, preconditions, test steps, expected results, test data, and notes.

## Edge case identification

### Categories to consider

1. **Null/empty values**

   - Null input
   - Empty string
   - Empty collection
   - Whitespace-only

1. **Boundary conditions**

   - Minimum value
   - Maximum value
   - Off-by-one errors

1. **Format variations**

   - Case sensitivity
   - Unicode characters
   - Special characters
   - Different encodings

1. **State-dependent**

   - First-time user
   - Returning user
   - Concurrent modifications

1. **External dependencies**

   - Network unavailable
   - Service timeout
   - Invalid response

### Edge case checklist

```markdown
## Edge case coverage for [Feature]

### Input validation
- [ ] Empty/null input
- [ ] Whitespace-only
- [ ] Maximum length
- [ ] Minimum length
- [ ] Special characters
- [ ] Unicode/emoji
- [ ] SQL injection attempt
- [ ] XSS attempt

### State conditions
- [ ] First use (no data)
- [ ] Single item
- [ ] Many items (pagination)
- [ ] Concurrent access
- [ ] Stale data

### Error conditions
- [ ] Network failure
- [ ] Service unavailable
- [ ] Invalid response
- [ ] Timeout
- [ ] Rate limited
```

## Validation checklist

Before considering a specification testable:

- [ ] Every requirement has at least one test case
- [ ] Happy path is covered for all features
- [ ] Error conditions have explicit test cases
- [ ] Boundary values are tested
- [ ] Security-sensitive features have security tests
- [ ] Performance requirements have measurable tests
- [ ] Test cases are traceable to requirements (TC-XXX -> REQ-XXX)
