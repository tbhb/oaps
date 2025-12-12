---
description: Add test cases to a specification
---

## Adding test cases to a specification

1. **Identify requirement(s) being tested** - Determine which requirements need test coverage:

   - Review requirement IDs that need testing
   - Understand the requirement's purpose and constraints

2. **Choose test method type** - Select the appropriate test method:

   - UT (unit test), NT (integration test), ET (end-to-end test), PT (performance test)
   - CT (conformance test), AT (accessibility test), ST (smoke test), MT (manual test)
   - Consider the requirement's nature and risk level

3. **Assign unique test ID** - Create a permanent test identifier:

   - Follow project's test ID convention
   - Ensure ID is never reused, even if test is deprecated

4. **Write test case using test-design techniques** - Apply systematic test design:

   - Use techniques from test-design reference
   - Consider state transitions, data flows, and interactions

5. **Apply equivalence partitioning and boundary analysis** - Ensure thorough coverage:

   - Identify valid and invalid input classes
   - Test boundary values and edge cases

6. **Fill in test-case template** - Complete all required fields:

   - Test steps, expected results, test data
   - Prerequisites, priority, and traceability

7. **Update tests.json** - Add test metadata to tracking file:

   - Include test ID, requirement IDs, and status
   - Maintain traceability matrix
