---
description: Split a specification into multiple focused files
---

## Split specification into multiple files

1. **Analyze spec size and section boundaries** - Assess the current specification structure:

   - Measure total line count and section sizes
   - Identify major section boundaries and their scope
   - Evaluate complexity and independence of each section

2. **Identify logical split points** - Determine how to divide the specification:

   - **By feature**: Separate distinct features into individual specs
   - **By layer**: Split frontend, backend, API, database concerns
   - **By audience**: Separate developer, user, and operations documentation

3. **Plan new file structure** - Design the multi-file organization:

   - Name each new specification file descriptively
   - Determine which content goes in each file
   - Plan a master index or overview file if needed
   - Establish naming conventions for the file set

4. **Preserve requirement/test IDs across split** - Maintain traceability:

   - Ensure all requirement IDs remain unique across files
   - Keep test case IDs consistent with their requirements
   - Document ID prefix conventions if using file-specific prefixes

5. **Create cross-reference links between files** - Establish connections:

   - Add links from requirements to related requirements in other files
   - Link test cases to requirements across file boundaries
   - Include "See also" sections pointing to related specifications

6. **Update index manifest** - Create navigation structure:

   - Build master index listing all specification files
   - Document the purpose and scope of each file
   - Establish reading order for sequential specifications

7. **Verify no orphaned requirements or tests** - Validate completeness:

   - Confirm all requirements from original spec are present
   - Ensure all test cases are included in split files
   - Check that no cross-references point to removed content
   - Verify the split specifications cover the full original scope
