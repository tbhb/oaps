---
description: Test hook rules for correct behavior
---

## Test hook rules

Use this workflow when validating hook rule behavior before deployment or debugging existing rules.

### Step 1: Validate syntax

Check rule structure:

- Run `oaps hooks validate` on configuration file
- Review any parsing errors or warnings
- Fix TOML syntax issues before proceeding
- Verify all required fields are present

### Step 2: Create test input fixtures

Prepare test scenarios:

- Create JSON files representing event contexts
- Include context for each event type the rule handles
- Design fixtures for expected matches (should trigger)
- Design fixtures for expected non-matches (should not trigger)
- Include edge case scenarios

### Step 3: Run hook tests

Execute validation:

- Use `oaps hooks test` with fixture files
- Test each rule individually first
- Then test rules in combination
- Compare actual results against expected behavior

### Step 4: Verify expected behavior

Confirm correct operation:

- Check that matching rules produce correct results
- Verify action execution (messages, logs, etc.)
- Confirm non-matching contexts are passed through
- Validate template substitution produces expected output

### Step 5: Test edge cases

Validate boundary conditions:

- Test with empty or null context values
- Test with unusual but valid inputs
- Test path edge cases (root, relative, special chars)
- Test git functions in non-git directories
- Test environment-dependent conditions

### Step 6: Test error conditions

Verify graceful handling:

- Test with malformed context data
- Test expression evaluation failures
- Verify error messages are helpful
- Check that errors don't crash the hook system

### Step 7: Test rule interactions

Validate combined behavior:

- Test rules with overlapping conditions
- Verify priority ordering works correctly
- Test terminal flag behavior
- Check that rule chaining produces expected results

### Step 8: Document test coverage

Record validation status:

- List scenarios tested for each rule
- Note any untested edge cases
- Document known limitations
- Create regression tests for bug fixes
- Add test fixtures to version control
