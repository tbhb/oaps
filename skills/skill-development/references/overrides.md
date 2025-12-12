---
name: overrides
title: Overriding and extending skills
description: Guidance on how projects can override references, workflows, and templates from builtin skills or add new ones. Covers the override directory structure and precedence rules.
principles:
  - Project overrides take precedence over builtin content
  - Overrides use a merge-and-replace strategy at the file level
  - New content can be added alongside overrides
  - Override structure mirrors the skill structure
best_practices:
  - "**Use overrides for project-specific content**: Keep builtin skills generic"
  - "**Mirror the structure**: Override directories match skill subdirectories"
  - "**Document overrides**: Note what was changed and why"
  - "**Prefer extension over replacement**: Add new files when possible"
checklist:
  - Override directory exists at .oaps/overrides/skills/<skill>/
  - Files use the same names as builtin files to override
  - New files have unique names to extend
  - Frontmatter is complete in override files
related:
  - skill-references
  - skill-workflows
  - templating
  - builtin-skills
---

## What are skill overrides

Skill overrides allow projects to customize builtin skills without modifying the original files. Projects can:

- **Override**: Replace builtin references, workflows, or templates with project-specific versions
- **Extend**: Add new references, workflows, or templates to builtin skills

Overrides use a merge-and-replace strategy: files with matching names replace builtin content, while new files extend the skill.

## Override locations

### Project skills

Create a full project skill to completely customize a skill:

```
.oaps/claude/skills/<skill-name>/
├── SKILL.md                  # Override skill metadata
├── references/               # Override/add references
├── workflows/                # Override/add workflows
├── templates/                # Override/add templates
├── scripts/                  # Override/add scripts
└── assets/                   # Override/add assets
```

Project skills in `.oaps/claude/skills/` take precedence over builtin skills in `skills/`.

### Override directory

For lighter-weight customization without a full skill, use the override directory:

```
.oaps/overrides/skills/<skill-name>/
├── references/               # Override/add references
├── workflows/                # Override/add workflows
└── templates/                # Override/add templates
```

Override directories extend builtin skills without replacing the SKILL.md.

## Precedence rules

### Skill loading order

When searching for a skill:

1. **Project skills** (`.oaps/claude/skills/<skill>/`) - highest precedence
2. **Builtin skills** (`skills/<skill>/`) - fallback

If a project skill exists, it completely shadows the builtin skill.

### Reference/workflow loading order

When loading references, workflows, or templates:

1. **Override directory** (`.oaps/overrides/skills/<skill>/`) - highest precedence
2. **Project skill** (`.oaps/claude/skills/<skill>/`) - if exists
3. **Builtin skill** (`skills/<skill>/`) - fallback

### Merge behavior

References, workflows, and templates are merged using `dict.update()`:

```python
# Pseudocode for merging
result = {}
result.update(builtin_content)   # Start with builtin
result.update(override_content)  # Override/extend with project
```

Files with matching names are replaced; new files are added.

## Overriding references

### Replace a builtin reference

To replace a builtin reference, create a file with the same name in the override directory:

**Builtin:** `skills/my-skill/references/patterns.md`
**Override:** `.oaps/overrides/skills/my-skill/references/patterns.md`

The override file completely replaces the builtin file.

### Add a new reference

To add a reference to a builtin skill, create a new file with a unique name:

**New:** `.oaps/overrides/skills/my-skill/references/project-patterns.md`

The new reference is merged with builtin references.

### Example: Override with project-specific content

```yaml
# .oaps/overrides/skills/python-practices/references/conventions.md
---
name: conventions
title: Project Python Conventions
description: Python conventions specific to this project. Overrides the builtin conventions reference.
---

## Import Order

This project uses a specific import order:

1. Standard library
2. Third-party packages
3. Local packages (with absolute imports)

## Naming Conventions

- Use `snake_case` for all functions and variables
- Use `PascalCase` for classes
- Prefix private modules with underscore: `_internal.py`
```

## Overriding workflows

### Replace a builtin workflow

**Builtin:** `skills/my-skill/workflows/standard.md`
**Override:** `.oaps/overrides/skills/my-skill/workflows/standard.md`

### Add a new workflow

**New:** `.oaps/overrides/skills/my-skill/workflows/quick.md`

### Change the default workflow

To change which workflow is the default, override the workflow and set `default: true`:

```yaml
# .oaps/overrides/skills/spec-writing/workflows/lightweight.md
---
name: lightweight
description: Quick spec for iterative development
default: true
---

## Lightweight Spec Workflow

1. Create a brief overview
2. List key requirements
3. Note any constraints
```

## Overriding templates

### Replace a builtin template

**Builtin:** `skills/spec-writing/templates/formal.md.j2`
**Override:** `.oaps/overrides/skills/spec-writing/templates/formal.md.j2`

### Add a new template

**New:** `.oaps/overrides/skills/spec-writing/templates/project-spec.md.j2`

### Example: Project-specific template

```jinja2
{# .oaps/overrides/skills/spec-writing/templates/project-spec.md.j2 #}
---
name: project-spec
description: Project-specific specification template with custom fields
---
---
title: {{ title }}
version: {{ version }}
status: {{ status }}
team: Platform
category: Infrastructure
---

# {{ title }}

## Project Context

This specification is part of the Platform team's infrastructure work.

## Requirements

- [ ] Requirement 1
- [ ] Requirement 2

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
```

## Full project skill override

For extensive customization, create a full project skill:

```
.oaps/claude/skills/python-practices/
├── SKILL.md                  # Custom skill metadata and workflow
├── references/
│   ├── conventions.md        # Project conventions (overrides builtin)
│   ├── testing.md            # Project testing practices (overrides builtin)
│   └── deployment.md         # New: deployment practices
└── workflows/
    └── review.md             # Project code review workflow
```

The project skill's SKILL.md can reference both overridden and new content.

## When to use each approach

### Use override directory when

- Adding a few references or workflows to a builtin skill
- Making minor customizations without changing the core skill
- Extending a skill's capabilities for project needs

### Use full project skill when

- Significantly changing the skill's workflow
- The skill needs a different description or triggers
- Most of the skill content is project-specific

### Keep builtin skills when

- The builtin skill meets project needs as-is
- Minor variations can be handled in the workflow
- Project consistency with OAPS defaults is preferred

## Example: OAPS project overrides

The OAPS project itself uses overrides to add development-specific content to the skill-development skill:

```
.oaps/overrides/skills/skill-development/
└── references/
    └── builtin-skills.md     # OAPS-specific builtin skill guidance
```

This adds guidance specific to developing OAPS builtin skills without modifying the generic skill-development skill that ships with the plugin.
