---
description: Remove a page from a multi-file specification
---

## Remove page from specification

1. **Identify all references to the page** - Audit dependencies:

   - Search for cross-references in other spec pages
   - Find references in test cases and test plans
   - Locate links in navigation and index structures
   - Check for references in implementation documentation

2. **Migrate or deprecate requirements on the page** - Handle existing requirements:

   - Determine which requirements are still needed
   - Move active requirements to appropriate remaining pages
   - Mark obsolete requirements as deprecated with rationale
   - Document migration decisions

3. **Update requirement IDs if requirements move** - Maintain traceability:

   - Renumber requirements to match target page ID scheme
   - Update requirement ID references throughout spec
   - Maintain version history showing ID changes
   - Add migration notes to moved requirements

4. **Update cross-references in other pages** - Fix broken links:

   - Replace references to removed page with new locations
   - Remove references if content is deprecated
   - Add explanatory notes where content was removed
   - Update "See also" sections

5. **Update spec manifest/index** - Remove page from tracking:

   - Delete entry from spec manifest or table of contents
   - Update navigation structures
   - Remove from any automated generation scripts

6. **Archive or delete the page** - Handle file removal:

   - Archive page to history/deprecated folder if preserving
   - Delete file completely if archiving not needed
   - Commit with clear message explaining removal rationale

7. **Verify no broken references** - Validate spec integrity:

   - Search for any remaining references to removed page
   - Check all cross-reference links still resolve
   - Verify requirement traceability is complete
   - Run spec validation tools if available
