---
description: Add a new reference document to a skill
---

## Add reference

### Step 1: Determine reference need

Identify what the reference should contain:

- What information does Claude need to complete specific tasks?
- Is this information currently in SKILL.md but should be extracted?
- Is this new information not yet documented?

Common reference types:

- Patterns and best practices
- API documentation
- Domain knowledge and schemas
- Checklists and validation criteria
- Advanced techniques and edge cases

### Step 2: Choose reference name

Select a descriptive name following conventions:

- Use lowercase with hyphens: `api-reference.md`, `patterns.md`
- Be specific: `testing-antipatterns.md` not just `testing.md`
- Group related concepts: `error-handling.md` for all error topics

### Step 3: Create reference file

Create the file in the skill's references directory:

```bash
touch <skill-path>/references/<name>.md
```

### Step 4: Add frontmatter

Add YAML frontmatter with required and optional fields:

```yaml
---
name: reference-name
title: Human-readable title
description: When to load this reference and what it covers
related:
  - other-reference
  - another-reference
commands:
  command-name: Description of what command does
principles:
  - Key principle one
  - Key principle two
best_practices:
  - Best practice one
  - Best practice two
checklist:
  - Checklist item one
  - Checklist item two
references:
  https://external-docs: External documentation link
---
```

### Step 5: Add content

Write the reference content:

- Use clear headings and structure
- Include concrete examples
- Keep under 10,000 words (if larger, split into multiple references)
- Use imperative/infinitive form for instructions
- Cross-reference related references where appropriate

### Step 6: Update workflow references

If any workflows should load this reference:

1. Open the relevant workflow file
1. Add the reference name to the `references:` array in frontmatter
1. Update workflow steps to mention the new reference if appropriate

### Step 7: Validate

Run validation to ensure the reference is properly structured:

```bash
oaps skill validate <skill-name>
```

### Step 8: Commit

Save the changes:

```bash
oaps skill save --message "add reference: <name>" <skill-name>
```
