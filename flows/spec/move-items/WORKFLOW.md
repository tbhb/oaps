---
description: Move requirements or test cases between specification pages
---

## Move items between specification pages

1. **Identify items to move and target location** - Define the move:

   - List specific requirements or test cases to relocate
   - Determine target page and section
   - Document rationale for the move
   - Check for any grouped items that should move together

2. **Verify target context is appropriate** - Validate placement:

   - Ensure target page scope matches item content
   - Check that target section structure accommodates items
   - Verify no semantic conflicts with existing content
   - Confirm target page maturity level matches item detail

3. **Update item IDs if moving between specs** - Maintain ID consistency:

   - Apply target spec's ID prefix and numbering scheme
   - Assign next available ID in target sequence
   - Record original ID in item metadata or version history
   - Add migration note showing old-to-new ID mapping

4. **Update cross-references in source and target** - Fix references:

   - Update references in source page to point to new location
   - Add cross-reference from target back to source if relevant
   - Update any "See also" sections in both pages
   - Fix inline references throughout specification

5. **Update test-to-requirement traceability** - Maintain test links:

   - Update test case references to new requirement IDs
   - Update requirement references to new test case IDs
   - Verify traceability matrix reflects new locations
   - Check that test coverage metrics remain accurate

6. **Verify no orphaned references** - Validate spec integrity:

   - Search for remaining references to old IDs
   - Confirm all cross-references resolve correctly
   - Check that moved items render properly in target context
   - Run spec validation tools if available
