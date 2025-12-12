---
description: Test hook rules for correct behavior
argument-hint: [rule-id]
allowed-tools:
  - AskUserQuestion
  - Bash(oaps:*)
  - Glob
  - Grep
  - Read
  - Skill
  - Task
  - TodoWrite
---

# Test hook rules

You are helping a developer validate hook rule behavior through systematic testing.

Test scope: $ARGUMENTS

## Workflow

1. **Load skill context** - Run `oaps skill context hook-rule-writing --references troubleshooting` to get detailed guidance

2. **Determine scope** - Based on arguments:
   - If rule ID provided: test that specific rule
   - If empty: validate all rules and offer to test specific ones

3. **Validate syntax** - Run `oaps hooks validate` to check configuration:
   - Report any parsing errors
   - Note any warnings
   - Fix syntax issues before proceeding with functional tests

4. **Create test scenarios** - For the target rule(s), create test fixtures:

   ```
   Design test scenarios for rule: [rule ID]

   Create JSON fixtures for:
   - Expected matches (should trigger the rule)
   - Expected non-matches (should not trigger)
   - Edge cases (boundary conditions)

   Each fixture should include the event context the rule evaluates against.
   ```

5. **Run tests** - Execute `oaps hooks test` with the fixtures:
   - Test each scenario
   - Compare actual vs expected results
   - Report any mismatches

6. **Verify behavior** - For matching rules, confirm:
   - Correct result type produced
   - Actions execute as expected
   - Template substitution works correctly
   - Priority ordering is correct

7. **Test edge cases** - Validate boundary conditions:
   - Empty or null context values
   - Unusual but valid inputs
   - Environment-dependent conditions
   - Git-dependent rules in non-git scenarios

8. **Present results** - Summarize test outcomes:
   - Passing scenarios
   - Failing scenarios with details
   - Edge cases that need attention
   - Recommendations for rule improvements

9. **Save fixtures** - If tests pass, offer to save fixtures for regression testing:
   - Launch hook-developer agent to create fixtures directory and save JSON files
   - Document test coverage
