---
description: Connect related ideas and maintain relationship metadata
---

## Link ideas workflow

Use this workflow to establish and document connections between ideas.

### Step 1: Identify the ideas

Determine which ideas to connect:

1. Identify the source idea (the one you're working on)
2. Identify the target idea(s) to link
3. Confirm both ideas exist and are accessible
4. Note current status of each idea

### Step 2: Determine relationship type

Classify the connection:

| Type | Description | Example |
|------|-------------|---------|
| supports | One idea strengthens another | Caching supports performance goals |
| conflicts | Ideas are mutually exclusive | Simplicity vs comprehensive features |
| extends | One idea builds on another | Mobile app extends web platform |
| combines | Ideas merge into something new | Search + recommendations = discovery |
| contrasts | Ideas illuminate by difference | Sync vs async processing |
| depends | One idea requires another | API requires authentication |
| supersedes | One idea replaces another | New approach replaces deprecated |
| related | General association | Same problem domain |

### Step 3: Document the connection

Update both idea documents:

**In source idea:**

1. Add target ID to `related_ideas` in frontmatter
2. Add connection note in Connections section:

   ```markdown
   ### Connection: IDEA-XXX
   **Type**: [relationship type]
   **Description**: [How they relate]
   **Implications**: [What this means for development]
   ```

**In target idea:**

1. Add source ID to `related_ideas` in frontmatter
2. Add reciprocal connection note:

   ```markdown
   ### Connection: IDEA-YYY
   **Type**: [inverse relationship type]
   **Description**: [How they relate from this perspective]
   ```

### Step 4: Analyze implications

Consider what the connection means:

1. Does this connection suggest new questions?
2. Are there shared constraints to consider?
3. Should exploration efforts be coordinated?
4. Are there shared resources or dependencies?
5. Does this affect prioritization of either idea?

Document insights in both ideas' development notes.

### Step 5: Update idea map (optional)

If maintaining a visual or structured map:

1. Add nodes for both ideas if not present
2. Draw edge with relationship type
3. Update any clustering or grouping
4. Check for emerging patterns in the map

### Step 6: Commit changes

Preserve the linkage:

1. Stage changes to both idea documents
2. Commit with message: "Link IDEA-XXX and IDEA-YYY: [relationship type]"
3. Update any indexes or tracking systems

### Step 7: Consider follow-up

Determine if action is needed:

- Should ideas be explored together?
- Does one idea inform refinement of the other?
- Are there other ideas that should also be linked?
- Does the connection suggest a new synthesized idea?
