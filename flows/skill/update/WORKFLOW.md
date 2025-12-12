---
description: Update an existing skill's core content
---

## Update skill

### Step 1: Read the existing skill

Read the complete skill to understand its current state:

- Read SKILL.md for core content and frontmatter
- Review all files in references/, workflows/, scripts/, templates/, and assets/
- Note the skill's purpose, trigger phrases, and structure

### Step 2: Identify changes needed

Determine what needs to be updated:

- Frontmatter changes (name, description, version)
- Body content changes (instructions, workflows, examples)
- Resource changes (scripts, references, assets, templates)
- Structural changes (reorganization, splitting, merging)

### Step 3: Update SKILL.md

Apply changes to SKILL.md while maintaining quality standards:

- Keep using imperative/infinitive form (verb-first instructions)
- Maintain third-person description with specific trigger phrases
- Keep body under 2,000 words
- Update version number if significant changes

### Step 4: Update related resources

If SKILL.md changes affect bundled resources:

- Update references that are mentioned in SKILL.md
- Update workflows that reference changed content
- Ensure cross-references remain valid

### Step 5: Validate the skill

Run validation to ensure the skill meets all requirements:

```bash
oaps skill validate <skill-name>
```

Fix any issues reported by validation.

### Step 6: Commit the changes

Save the updated skill:

```bash
oaps skill save --message "update: <description of changes>" <skill-name>
```
