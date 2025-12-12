---
description: Archive workflow for preserving inactive ideas
---

## Archive idea workflow

Use this workflow to archive ideas that are no longer being actively developed.

### Step 1: Review current state

Assess the idea before archiving:

1. Read the complete idea document
2. Note the current status
3. Review development history
4. Identify why archiving is appropriate:
   - Superseded by another idea
   - No longer relevant
   - Blocked by insurmountable constraints
   - Completed and applied
   - Exploration concluded without viable path

### Step 2: Create final summary

Document the idea's conclusion:

1. Write a final status summary:

   ```markdown
   ### Archive summary
   **Archived**: [Date]
   **Reason**: [Why archiving]
   **Status at archive**: [seed/exploring/refining/crystallized]
   **Key learnings**: [What was valuable]
   **Successor ideas**: [If superseded, link to new ideas]
   ```

2. Summarize the most valuable insights gained
3. Note any reusable components or patterns
4. Document what would need to change for revival

### Step 3: Update connections

Maintain relationship integrity:

1. Review all linked ideas in `related_ideas`
2. Update those ideas to note this archive
3. Check if any ideas depend on this one
4. Update dependent ideas with archive status
5. Remove from active indexes if applicable

### Step 4: Update status

Finalize the archive:

1. Update status to `archived`
2. Update the `updated` date
3. Add archive reason to frontmatter:

   ```yaml
   archive_reason: [reason]
   archive_date: [date]
   ```

4. Move to archive location if using separate storage

### Step 5: Preserve learnings

Extract value before closing:

1. Document reusable patterns or techniques
2. Note questions that remain interesting
3. Identify insights applicable to other work
4. Create references from valuable content

### Step 6: Commit

Preserve the archived state:

1. Commit with message: "Archive IDEA-NNN: [title] - [reason]"
2. Tag if using version control tags for archives
3. Update any tracking systems or indexes
