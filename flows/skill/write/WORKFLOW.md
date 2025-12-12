---
description: Create a new skill from scratch
default: true
---

## Create skill

Follow these steps in order, skipping steps only when there is a clear reason why they are not applicable.

### Step 1: Understand the skill with concrete examples

Skip this step only when the skill's usage patterns are already clearly understood. It remains valuable even when working with an existing skill.

To create an effective skill, clearly understand concrete examples of how the skill will be used. This understanding can come from either direct user examples or generated examples validated with user feedback.

For example, when building an image-editor skill, relevant questions include:

- "What functionality should the image-editor skill support? Editing, rotating, anything else?"
- "Can you give some examples of how this skill would be used?"
- "I can imagine users asking for things like 'Remove the red-eye from this image' or 'Rotate this image'. Are there other ways you imagine this skill being used?"
- "What would a user say that should trigger this skill?"

To avoid overwhelming users, avoid asking too many questions in a single message. Start with the most important questions and follow up as needed.

Conclude this step when there is a clear sense of the functionality the skill should support.

### Step 2: Plan reusable skill contents

To turn concrete examples into an effective skill, analyze each example by:

1. Considering how to execute on the example from scratch
1. Identifying what scripts, references, and assets would be helpful when executing these workflows repeatedly

Example analyses:

- **PDF rotation skill**: Rotating a PDF requires re-writing the same code each time → A `scripts/rotate_pdf.py` script would be helpful
- **Frontend webapp builder skill**: Writing a frontend webapp requires the same boilerplate each time → An `assets/hello-world/` template would be helpful
- **BigQuery skill**: Querying BigQuery requires re-discovering table schemas each time → A `references/schema.md` file would be helpful

To establish the skill's contents, analyze each concrete example to create a list of reusable resources to include: scripts, references, and assets.

### Step 3: Initialize the skill

Skip this step only if the skill being developed already exists and iteration or packaging is needed.

When creating a new skill from scratch, always run the `oaps skill create` command:

```bash
oaps skill create <skill-name>
```

The command:

- Creates the skill directory in the project skills directory: `.oaps/claude/skills/<skill-name>/`
- Generates a SKILL.md template with proper frontmatter and TODO placeholders
- Creates example resource directories: `scripts/`, `references/`, and `assets/`
- Adds example files in each directory that can be customized or deleted

After initialization, customize or remove the generated SKILL.md and example files as needed.

### Step 4: Edit the skill

When editing the skill, remember that the skill is being created for another instance of Claude to use. Focus on including information that would be beneficial and non-obvious to Claude.

#### Start with reusable skill contents

To begin implementation, start with the reusable resources identified in Step 2: `scripts/`, `references/`, and `assets/` files. Note that this step may require user input. For example, when implementing a `brand-guidelines` skill, the user may need to provide brand assets or templates.

Also, delete any example files and directories not needed for the skill. The initialization script creates example files to demonstrate structure, but most skills won't need all of them.

#### Update SKILL.md

**Writing style:** Write the entire skill using **imperative/infinitive form** (verb-first instructions), not second person. Use objective, instructional language (e.g., "To accomplish X, do Y" rather than "You should do X").

**Description (frontmatter):** Use third-person format with specific trigger phrases:

```yaml
---
name: Skill Name
description: This skill should be used when the user asks to "specific phrase 1", "specific phrase 2", "specific phrase 3". Include exact phrases users would say that should trigger this skill.
version: 0.1.0
---
```

**Good description examples:**

```yaml
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse hook", "validate tool use", or mentions hook events (PreToolUse, PostToolUse, Stop).
```

**Bad description examples:**

```yaml
description: Use this skill when working with hooks.  # Wrong person, vague
description: Load when user needs hook help.  # Not third person
description: Provides hook guidance.  # No trigger phrases
```

To complete SKILL.md, answer the following questions:

1. What is the purpose of the skill, in a few sentences?
1. When should the skill be used? (Include this in frontmatter description with specific triggers)
1. In practice, how should Claude use the skill? All reusable skill contents developed above should be referenced so that Claude knows how to use them.

**Keep SKILL.md lean:** Target 1,500-2,000 words for the body. Move detailed content to references.

### Step 5: Validate the skill

To ensure the skill is well-structured and effective, validate and test it before committing:

```bash
oaps skill validate <skill-name>
```

The validation command checks:

- Skill naming conventions and directory structure
- YAML frontmatter format and required fields
- Description completeness and quality
- Body writing style and clarity
- SKILL.md length (1,500-2,000 words)
- File organization and resource references

If validation fails, the command will report the errors. Fix any issues and run the validation command again until it passes.

### Step 6: Add activation hooks

Activation hooks help users discover the skill automatically by detecting keywords in prompts or file operations and suggesting the skill without blocking.

**For built-in OAPS skills** (in `skills/` at project root):

Add activation hooks in `src/oaps/hooks/builtin/skills.toml`:

1. Add a `[[rules]]` section to `src/oaps/hooks/builtin/skills.toml`
2. Use `user_prompt_submit` events for keyword-based triggers
3. Use `pre_tool_use` events for file-based triggers
4. Set priority to `high` for suggestions, `critical` for enforcement
5. Use `suggest` action type with a helpful message
6. Add unit tests in `tests/unit/hooks/test_builtin_hooks.py`

**For project-specific skills** (in `.oaps/claude/skills/`):

Add activation hooks in `.oaps/hooks.d/skills.toml`:

1. Create `.oaps/hooks.d/skills.toml` if it doesn't exist
2. Follow the same rule format as built-in hooks
3. No unit tests required for project-specific hooks

For regex patterns and testing examples, see `references/activation-hooks.md`.

### Step 7: Commit the skill

Once the skill is ready, commit it to the project's .oaps repository. The saving process automatically validates the skill first:

```bash
oaps skill save --message "skill created" <skill-name>
```

**MANDATORY:** Always use the `oaps skill save` command to save skills instead of manually committing them. This ensures proper validation and consistent commit formatting.

### Step 8: Iterate

After testing the skill, users may request improvements. Often this happens right after using the skill, with fresh context of how the skill performed.

**Iteration workflow:**

1. Use the skill on real tasks
1. Notice struggles or inefficiencies
1. Identify how SKILL.md or bundled resources should be updated
1. Implement changes and test again

**Common improvements:**

- Strengthen trigger phrases in description
- Move long sections from SKILL.md to references/
- Add missing examples or scripts
- Clarify ambiguous instructions
- Add edge case handling
