---
description: Update existing requirements
---

## Update requirements

1. **Identify requirements to update by ID** - Locate target requirements:

   - Search specification for requirement IDs
   - Verify requirement exists and is current
   - Check requirement status (not deprecated)

2. **Preserve requirement ID (permanent)** - Maintain traceability:

   - Never change requirement IDs
   - IDs are permanent identifiers
   - Changes tracked through version history

3. **Apply changes following requirement-writing principles** - Update requirement text:

   - Maintain atomic structure (single testable statement)
   - Use clear, unambiguous language
   - Use "shall" consistently for all requirements
   - Reference requirement-writing reference for guidance

4. **Update affected acceptance criteria** - Revise test conditions:

   - Align acceptance criteria with updated requirement
   - Add new criteria for new functionality
   - Remove obsolete criteria
   - Ensure complete test coverage

5. **Check impact on dependent requirements** - Analyze ripple effects:

   - Identify parent requirements that may need updates
   - Identify child requirements that may be affected
   - Check cross-referenced requirements
   - Update dependent requirements if needed

6. **Update traceability to test cases** - Maintain test linkage:

   - Verify existing test cases still apply
   - Identify test cases needing updates
   - Add new test cases if needed
   - Update test case documentation

7. **Document changes in spec history** - Record modification:

   - Add entry to change log or history section
   - Include date, author, and reason for change
   - Reference related requirements or issues
   - Increment specification version if appropriate
