---
description: Update an existing reference document
---

## Update reference

### Step 1: Read the reference

Read the complete reference file:

- Understand its current content and structure
- Note the frontmatter fields
- Identify the target audience and use cases

### Step 2: Identify changes needed

Determine what needs to be updated:

- **Frontmatter changes**: name, title, description, related, commands, principles, best_practices, checklist, references
- **Content changes**: new sections, updated examples, clarifications
- **Structural changes**: reorganization, splitting, merging

### Step 3: Update frontmatter

If frontmatter changes are needed:

- Update `description` if the reference scope changed
- Update `related` if new references were added or removed
- Update `commands` if new CLI commands are relevant
- Update `principles`, `best_practices`, or `checklist` as needed

### Step 4: Update content

Apply content changes:

- Maintain consistent writing style (imperative/infinitive form)
- Keep content under 10,000 words
- Update examples to reflect current best practices
- Ensure cross-references to other documents are still valid

### Step 5: Check related references

If this reference is mentioned in other documents:

```bash
grep -r "<reference-name>" <skill-path>/references/
```

Update any documents that depend on content that changed.

### Step 6: Check workflows

If this reference is used by workflows:

```bash
grep -r "<reference-name>" <skill-path>/workflows/
```

Ensure workflow steps still make sense with the updated content.

### Step 7: Validate

Run validation:

```bash
oaps skill validate <skill-name>
```

### Step 8: Commit

Save the changes:

```bash
oaps skill save --message "update reference: <name>" <skill-name>
```
