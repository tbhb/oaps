---
description: Remove a template from a skill
---

## Remove template

### Step 1: Identify the template

Locate the template file to remove:

```bash
ls <skill-path>/templates/
```

Read the template to understand what it generates and why it might be removed.

### Step 2: Check for usage

Search for references to this template in workflows and references:

```bash
grep -r "<template-name>" <skill-path>/
```

Note all files that mention or use this template.

### Step 3: Update referencing documents

For each document that references this template:

1. Remove references to the template
1. Update any instructions that mention the template
1. Consider if alternative templates should be suggested

### Step 4: Remove the template file

Delete the template file:

```bash
rm <skill-path>/templates/<name>
```

### Step 5: Clean up templates directory

If the templates directory is now empty, consider removing it:

```bash
rmdir <skill-path>/templates/  # Only works if empty
```

### Step 6: Validate

Run validation:

```bash
oaps skill validate <skill-name>
```

### Step 7: Commit

Save the changes:

```bash
oaps skill save --message "remove template: <name>" <skill-name>
```
