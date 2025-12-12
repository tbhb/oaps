---
description: Workflow for writing new tests
---

## Writing new tests

Use this workflow when writing new tests for existing or new code.

1. **Identify what to test** - Focus on behavior, not implementation. Ask "What should this code accomplish?"

2. **Write test names first** - Use `test_<scenario>_<expected>` format to clarify intent before writing code

3. **Verify test can fail** - Before finishing, temporarily break the code to confirm the test catches it

4. **Check for antipatterns** - Review against the testing-antipatterns checklist

5. **Run quality checks**:
   - `just test` - All tests pass
   - `just test-coverage` - Maintain >95% coverage
