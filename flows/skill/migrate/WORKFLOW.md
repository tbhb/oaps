---
description: Migrate an existing monolithic skill to OAPS's progressive disclosure system
---

## Migrate skill

This workflow adapts an existing SKILL.md file from another project to OAPS's skill system with progressive disclosure: lightweight SKILL.md, references, and workflows.

### Step 1: Locate source skill

Obtain the path to the existing skill file to migrate:

- Ask the user for the file path if not provided
- Verify the file exists and is readable
- Confirm the file is a SKILL.md or equivalent skill definition

### Step 2: Analyze source skill

Read the source skill thoroughly to understand its structure:

1. Read the entire source file
2. Identify the skill's core purpose and domain
3. Note the trigger phrases and activation patterns
4. List all distinct sections and their purposes
5. Identify multi-step procedures embedded in the content
6. Estimate word count and identify areas exceeding OAPS guidelines

**Categorize content into:**

- **Essential** - Core purpose, main workflow, key concepts (stays in SKILL.md)
- **Reference material** - Detailed documentation, patterns, examples (becomes references/)
- **Procedures** - Multi-step workflows, specific task guides (becomes workflows/)

### Step 3: Design OAPS structure

Plan the decomposition based on the analysis:

1. **SKILL.md scope** - Identify content for the lean SKILL.md (target 1,500-2,000 words):
   - Skill name and description with trigger phrases
   - Core purpose and when to use
   - High-level workflow or process
   - Pointers to references and workflows

2. **References to create** - Plan reference files for detailed content:
   - Group related detailed content logically
   - Name using descriptive, hyphenated names (e.g., `patterns.md`, `api-reference.md`)
   - Include frontmatter requirements (name, title, description, related, principles, best_practices, checklist)

3. **Workflows to create** - Plan workflow files for procedures:
   - Identify distinct multi-step tasks
   - Name using verb-noun convention (e.g., `create-spec.md`, `review-code.md`)
   - Determine which references each workflow needs

Present the decomposition plan to the user for approval before proceeding.

### Step 4: Initialize the skill

Create the skill directory structure:

```bash
oaps skill create <skill-name>
```

This creates:

- `.oaps/claude/skills/<skill-name>/`
- `SKILL.md` template with proper frontmatter
- Example `scripts/`, `references/`, and `assets/` directories

### Step 5: Create lightweight SKILL.md

Write the lean SKILL.md following OAPS standards:

**Frontmatter:**

```yaml
---
name: Skill Name
description: This skill should be used when the user asks to "trigger phrase 1", "trigger phrase 2", or needs guidance on specific domain.
version: 0.1.0
---
```

**Body requirements:**

- Use imperative/infinitive form (verb-first instructions)
- Target 1,500-2,000 words maximum
- Include core purpose and high-level workflow
- Reference detailed content with pointers: "For detailed patterns, see `references/patterns.md`"
- Do not duplicate content that will be in references

### Step 6: Extract references

Create reference files for detailed content:

1. For each planned reference, create `references/<name>.md`

2. Add proper frontmatter:

   ```yaml
   ---
   name: reference-name
   title: Human-Readable Title
   description: Brief description of what this reference covers
   related:
     - other-reference-name
   principles:
     - Key principle 1
     - Key principle 2
   best_practices:
     - Best practice 1
     - Best practice 2
   checklist:
     - Checklist item 1
     - Checklist item 2
   commands:
     command-name: Description of command
   references:
     https://example.com: External reference description
   ---
   ```

3. Move detailed content from the source skill, adapting to imperative form

4. Cross-reference related content between references

### Step 7: Create workflows

Create workflow files for multi-step procedures:

1. For each planned workflow, create `workflows/<verb-noun>.md`

2. Add proper frontmatter:

   ```yaml
   ---
   name: workflow-name
   description: Brief description of what this workflow does
   default: false
   references:
     - reference-name-1
     - reference-name-2
   ---
   ```

3. Structure as numbered steps with clear completion criteria:

   ```markdown
   ## Workflow Title

   ### Step 1: Step name

   Step instructions...

   ### Step 2: Step name

   Step instructions...
   ```

4. Designate one workflow as `default: true` (usually the main creation workflow)

### Step 8: Validate

Run validation to ensure proper structure:

```bash
oaps skill validate <skill-name>
```

**Validation checks:**

- Frontmatter format and required fields
- Description with trigger phrases
- SKILL.md word count (1,500-2,000)
- Reference and workflow structure
- Cross-reference validity

Fix any issues reported by validation.

### Step 9: Commit

Save the migrated skill:

```bash
oaps skill save --message "migrate skill from <source>" <skill-name>
```

**Post-migration checklist:**

- [ ] SKILL.md is under 2,000 words
- [ ] All detailed content moved to references
- [ ] Multi-step procedures extracted to workflows
- [ ] Frontmatter complete with trigger phrases
- [ ] References properly cross-linked
- [ ] Workflows specify their required references
- [ ] Validation passes
