---
name: skill-references
title: Creating skill references
description: Guidance on creating and organizing reference files within skills. Covers when to use references vs SKILL.md, file structure, frontmatter format, and organization patterns.
principles:
  - References keep SKILL.md lean while providing detailed information on-demand
  - Information should live in one place only - either SKILL.md or references
  - References are loaded when Claude determines they are needed
  - Large references should include grep patterns for targeted searches
best_practices:
  - "**Single source of truth**: Avoid duplicating content between SKILL.md and references"
  - "**Descriptive names**: Use names that indicate content (patterns.md, api-reference.md)"
  - "**Frontmatter metadata**: Include name, title, description for discoverability"
  - "**Size awareness**: Keep references under 10k words; split larger content"
  - "**Cross-references**: Link between related references when helpful"
checklist:
  - Reference has descriptive filename
  - Frontmatter includes name, title, description
  - Content is not duplicated from SKILL.md
  - Large files include grep search patterns in SKILL.md
  - Related references are cross-linked
related:
  - skill-workflows
  - builtin-skills
---

## What are skill references

References are documentation files within a skill's `references/` directory. They provide detailed information that Claude can load on-demand, keeping the main SKILL.md lean while making comprehensive documentation available when needed.

References follow the progressive disclosure principle: they are not loaded when the skill activates, but Claude can read them when the task requires deeper knowledge.

## When to use references vs SKILL.md

### Keep in SKILL.md

- Core procedural instructions (the "how to use this skill" workflow)
- Essential context needed for every task
- Brief overviews and summaries
- Links to references for detailed information

### Move to references

- Detailed patterns and examples
- API documentation and schemas
- Advanced techniques and edge cases
- Domain-specific knowledge bases
- Configuration reference tables
- Migration guides and troubleshooting

### Decision guide

Ask: "Does Claude need this information for every task, or only sometimes?"

- **Every task** → SKILL.md
- **Sometimes** → references/

## Reference file structure

### Directory layout

```
skill-name/
├── SKILL.md
└── references/
    ├── patterns.md           # Common patterns and examples
    ├── api-reference.md      # API documentation
    ├── advanced.md           # Advanced techniques
    └── troubleshooting.md    # Common issues and solutions
```

### Frontmatter format

Every reference should include YAML frontmatter:

```yaml
---
name: patterns
title: Common patterns for X
description: Reference for patterns used in X. Includes examples for Y and Z scenarios.
principles:
  - Key principle 1
  - Key principle 2
best_practices:
  - "**Practice name**: Description of the practice"
checklist:
  - Checklist item 1
  - Checklist item 2
related:
  - other-reference
  - another-reference
---
```

### Frontmatter fields

| Field            | Required | Purpose                                         |
|:-----------------|:---------|:------------------------------------------------|
| `name`           | Yes      | Short identifier (matches filename without .md) |
| `title`          | Yes      | Human-readable title                            |
| `description`    | Yes      | When to load this reference                     |
| `principles`     | No       | Guiding principles for the topic                |
| `best_practices` | No       | Recommended approaches                          |
| `checklist`      | No       | Verification items                              |
| `commands`       | No       | Related CLI commands                            |
| `related`        | No       | Links to related references                     |

## Naming conventions

### File naming

- Use lowercase with hyphens: `api-reference.md`, `common-patterns.md`
- Be descriptive: `database-schemas.md` not `schemas.md`
- Group related content: `testing-patterns.md`, `testing-fixtures.md`

### Common reference names

| Name                 | Content                      |
|:---------------------|:-----------------------------|
| `patterns.md`        | Common patterns and examples |
| `api-reference.md`   | API documentation            |
| `advanced.md`        | Advanced techniques          |
| `configuration.md`   | Configuration options        |
| `troubleshooting.md` | Common issues and solutions  |
| `migration.md`       | Migration guides             |
| `examples.md`        | Extended examples            |

## Size guidelines

### Target sizes

- **SKILL.md body**: 1,500-2,000 words
- **Individual references**: Under 10,000 words
- **Total skill size**: No hard limit, but consider splitting into multiple skills if very large

### When to split references

Split a reference when:

- It exceeds 10,000 words
- It covers multiple distinct topics
- Different sections are needed for different tasks

Example split:

```
# Before: one large file
references/
└── api-reference.md (15,000 words)

# After: split by domain
references/
├── api-authentication.md
├── api-endpoints.md
└── api-errors.md
```

### Large reference handling

For references over 5,000 words, add grep patterns in SKILL.md:

```markdown
For database schema details, see `references/schemas.md`.
Search patterns:
- User tables: `grep -n "## User" references/schemas.md`
- Order tables: `grep -n "## Order" references/schemas.md`
```

## How Claude discovers references

Claude discovers references through:

1. **Explicit mentions in SKILL.md**: "See `references/patterns.md` for examples"
2. **Frontmatter descriptions**: Claude reads descriptions to determine relevance
3. **Directory listing**: Claude can list the references/ directory
4. **Cross-references**: Links between references guide navigation

### Writing discoverable descriptions

Good description:

```yaml
description: Database schema reference for the user management system.
  Load when working with user tables, authentication, or permissions queries.
```

Poor description:

```yaml
description: Schema reference.
```

## Organization patterns

### By topic

Organize references by subject area:

```
references/
├── authentication.md
├── authorization.md
├── data-models.md
└── api-endpoints.md
```

### By task type

Organize by what Claude is doing:

```
references/
├── creating-resources.md
├── querying-data.md
├── handling-errors.md
└── testing-patterns.md
```

### By complexity

Organize by skill level:

```
references/
├── getting-started.md
├── common-patterns.md
├── advanced-techniques.md
└── edge-cases.md
```

## Cross-referencing

### Linking between references

Use the `related` frontmatter field:

```yaml
related:
  - patterns
  - troubleshooting
```

### Inline references

Reference other files inline:

```markdown
For authentication patterns, see `references/authentication.md`.
```

### Avoiding circular dependencies

Keep references self-contained where possible. If A references B and B references A, ensure each can be understood independently.

## Examples

### Good reference organization

The `hook-rule-writing` skill demonstrates good organization:

```
hook-rule-writing/
├── SKILL.md                    # Core workflow and concepts
└── references/
    └── builtin-hooks.md        # Detailed builtin hook reference
```

SKILL.md contains the workflow; the reference contains detailed documentation about builtin hooks.

### Reference with frontmatter

```yaml
---
name: database-schemas
title: Database schema reference
description: Complete schema documentation for the application database.
  Load when writing queries, creating migrations, or debugging data issues.
commands:
  psql -d mydb -c "\\dt": List all tables
  psql -d mydb -c "\\d users": Describe users table
principles:
  - All tables use UUID primary keys
  - Timestamps are stored in UTC
  - Soft deletes use deleted_at column
checklist:
  - Foreign keys have appropriate indexes
  - Timestamps include timezone info
  - Column names use snake_case
related:
  - migrations
  - queries
---

## Users table

The users table stores...
```
