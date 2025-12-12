---
description: Remove test cases from a specification
---

## Removing test cases from a specification

1. **Identify test cases to remove by ID** - Locate specific tests to delete:

   - Use test IDs to find exact test cases
   - Understand why test is being removed

2. **Check if removal creates coverage gaps** - Assess impact on test coverage:

   - Review what scenarios the test covered
   - Determine if other tests cover same scenarios

3. **Verify requirement still has adequate coverage** - Ensure requirements remain tested:

   - Check that related requirements have other tests
   - Confirm no critical scenarios are lost

4. **Mark test case as deprecated** - Preserve test ID history:

   - IDs are never reused, even after deletion
   - Document deprecation reason and date

5. **Update tests.json** - Remove test from tracking:

   - Mark test as deprecated in metadata
   - Maintain historical record of test ID

6. **Document removal in spec history** - Record the change:

   - Explain why test was removed
   - Note any replacement tests if applicable
