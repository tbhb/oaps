---
description: Review an existing skill for quality and completeness
---

## Review skill

### Step 1: Read the complete skill

Read all skill files to understand the full context:

- SKILL.md (core content and frontmatter)
- All files in references/
- All files in workflows/
- All files in scripts/, templates/, assets/

### Step 2: Check frontmatter quality

Verify SKILL.md frontmatter meets requirements:

- **name**: Present and matches directory name
- **description**: Uses third-person, includes specific trigger phrases
- **version**: Present and follows semantic versioning

**Good description pattern:**

```yaml
description: This skill should be used when the user asks to "phrase 1", "phrase 2", "phrase 3", or needs guidance on [topic].
```

### Step 3: Verify progressive disclosure

Check that content is properly distributed:

- SKILL.md is lean (under 2,000 words)
- Detailed content lives in references/
- Task-specific procedures live in workflows/
- No duplication between SKILL.md and references

### Step 4: Validate resource organization

Check that resources are properly organized:

- Scripts in scripts/ are executable and documented
- References in references/ have proper frontmatter
- Workflows in workflows/ have proper frontmatter with references array
- Templates in templates/ use .j2 extension for Jinja files
- Assets in assets/ are appropriately categorized

### Step 5: Check writing style

Verify consistent writing style:

- Uses imperative/infinitive form (verb-first instructions)
- Does not use second person ("you should...")
- Uses objective, instructional language
- Steps have clear completion criteria

### Step 6: Run validation command

Execute the validation command:

```bash
oaps skill validate <skill-name>
```

### Step 7: Document findings

Record review results organized by category:

- **Critical**: Blocks skill functionality
- **Major**: Reduces clarity or effectiveness
- **Minor**: Style or formatting improvements

Include specific examples and references for each finding.
