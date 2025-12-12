---
description: Workflow for reviewing existing tests
---

## Reviewing tests

Use this workflow when reviewing tests in code reviews or auditing test quality.

1. **Ask the key question** - "What bug would cause this test to fail?" If no clear answer, the test has no value

2. **Check for antipatterns**:
   - Tautological tests (asserting what was just set up)
   - Testing mocks instead of code
   - No meaningful assertions
   - Mirrored implementation logic
   - Tests that cannot fail
   - Implementation testing instead of behavior testing

3. **Verify test isolation** - Each test should set up its own state, not depend on other tests

4. **Check naming** - Names should describe scenario and expected outcome
