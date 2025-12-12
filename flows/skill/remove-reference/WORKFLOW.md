---
description: Remove a reference document from a skill
---

## Remove reference

### Step 1: Identify the reference

Locate the reference file to remove:

```bash
ls <skill-path>/references/
```

Read the reference to understand what it contains and why it might be removed.

### Step 2: Check for usage in workflows

Search for workflows that reference this document:

```bash
grep -r "<reference-name>" <skill-path>/workflows/
```

Note all workflows that include this reference in their `references:` array.

### Step 3: Check for cross-references

Search for references that link to this document:

```bash
grep -r "<reference-name>" <skill-path>/references/
```

Note all references that mention or link to this document.

### Step 4: Update referencing workflows

For each workflow that references this document:

1. Open the workflow file
1. Remove the reference name from the `references:` array
1. Update any steps that mention the reference
1. Consider if the workflow still makes sense without this reference

### Step 5: Update cross-referencing documents

For each reference that links to this document:

1. Open the reference file
1. Remove or update links to the deleted reference
1. Update the `related:` array if present

### Step 6: Remove the reference file

Delete the reference file:

```bash
rm <skill-path>/references/<name>.md
```

### Step 7: Validate

Run validation to ensure the skill still works correctly:

```bash
oaps skill validate <skill-name>
```

Fix any broken references or missing content.

### Step 8: Commit

Save the changes:

```bash
oaps skill save --message "remove reference: <name>" <skill-name>
```
