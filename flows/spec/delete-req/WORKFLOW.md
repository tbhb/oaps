---
description: Remove requirements from a specification
---

## Remove requirements

1. **Identify requirements to remove by ID** - Locate target requirements:

   - Search specification for requirement IDs
   - Verify requirements exist and are current
   - Document reason for removal

2. **Check for dependent requirements** - Analyze impact:

   - Identify parent requirements that reference this requirement
   - Identify child requirements that depend on this requirement
   - Check cross-references from other requirements
   - Document all dependencies

3. **Identify test cases that trace to these requirements** - Find affected tests:

   - Search test documentation for requirement ID references
   - List all test cases linked to the requirement
   - Check test coverage impact
   - Document test cases for handling decision

4. **Decide on test case handling** - Determine test fate:

   - Delete: Remove obsolete tests
   - Reassign: Link tests to replacement requirements
   - Archive: Preserve tests for historical reference
   - Document decision rationale

5. **Mark requirement as deprecated (IDs never reused)** - Update requirement status:

   - Change requirement status to "deprecated" or "removed"
   - Add deprecation date and reason
   - Never delete requirement ID from tracking system
   - IDs are permanent and never reused

6. **Update requirements.json** - Maintain requirement metadata:

   - Update requirement status to deprecated
   - Remove from active requirement count
   - Preserve entry for historical traceability
   - Update affected traceability links

7. **Document removal in spec history** - Record deletion:

   - Add entry to change log or history section
   - Include date, author, and reason for removal
   - Reference replacement requirements if applicable
   - Increment specification version if appropriate
