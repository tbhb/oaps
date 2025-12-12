---
description: Review and assess specification file organization
---

## Specification organization review

1. **Analyze current section ordering** - Compare document structure against specification conventions:

   - Check if sections follow standard ordering (overview, requirements, design, tests, etc.)
   - Identify sections that deviate from conventional placement
   - Note any missing expected sections

2. **Identify redundant or misplaced content** - Find content that needs relocation or consolidation:

   - Look for duplicate information across sections
   - Identify content in wrong sections (e.g., implementation details in requirements)
   - Flag content that belongs in separate specifications

3. **Check header hierarchy and document flow** - Verify structural consistency:

   - Ensure header levels progress logically (no skipped levels)
   - Verify each section flows naturally to the next
   - Check that subsections are appropriately nested

4. **Verify cross-references are valid** - Validate all internal and external links:

   - Test requirement ID references point to existing requirements
   - Check test case references link correctly
   - Verify external specification references are accurate

5. **Assess whether split into multiple files is warranted** - Evaluate if specification should be divided:

   - Check if document exceeds reasonable length (>500 lines as guideline)
   - Identify distinct features/components that could be separate specs
   - Evaluate if audience needs differ across sections (developer vs. user)

6. **Recommend reorganization with specific actions** - Provide actionable improvement plan:

   - List specific sections to move, merge, or split
   - Suggest new section ordering if needed
   - Identify content to extract into separate files
   - Provide rationale for each recommendation
