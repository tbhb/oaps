---
name: templating
title: Jinja templating in skills
description: Guidance on using Jinja2 templating in skill references, workflows, and templates. Covers available context variables, frontmatter templating, and template patterns.
principles:
  - Templates enable dynamic content based on project context
  - Frontmatter values can themselves be templated
  - Context is composed from base, component, and user layers
  - Templates use standard Jinja2 syntax
best_practices:
  - "**Provide defaults**: Use `{{ var or 'default' }}` for optional variables"
  - "**Keep templates readable**: Avoid complex logic in templates"
  - "**Document variables**: List required context in frontmatter description"
  - "**Test rendering**: Verify templates render correctly with different contexts"
checklist:
  - Template uses valid Jinja2 syntax
  - Required variables are documented
  - Optional variables have defaults
  - Frontmatter renders correctly
related:
  - skill-references
  - skill-workflows
  - overrides
---

## What is templating in skills

OAPS skills support Jinja2 templating in references, workflows, and template files. This enables dynamic content that adapts to the project context, tool versions, and user-provided values.

Templating uses the standard Jinja2 `{{ variable }}` syntax.

## Where templating works

### References

Reference files (`.md` in `references/`) support templating in both:

- **Frontmatter values**: Metadata fields can use template variables
- **Body content**: The main content can use template variables

### Workflows

Workflow files (`.md` in `workflows/`) support templating in:

- **Body content**: The workflow steps can use template variables
- Note: Workflow frontmatter does not support templating

### Templates

Template files (`.md.j2` in `templates/`) support full templating in:

- **Frontmatter values**: Dynamic metadata
- **Body content**: Dynamic content generation

## Available context variables

### Base context (always available)

| Variable        | Type          | Description                                    |
|:----------------|:--------------|:-----------------------------------------------|
| `today`         | `date`        | Current date                                   |
| `author_name`   | `str \| None` | Author name from environment or git config     |
| `author_email`  | `str \| None` | Author email from environment or git config    |
| `tool_versions` | `dict`        | Detected tool versions (Python, Node.js, etc.) |

### Skill context

When loading references and workflows:

| Variable        | Type   | Description            |
|:----------------|:-------|:-----------------------|
| `tool_versions` | `dict` | Detected tool versions |

### Specification context

When rendering spec templates:

| Variable  | Type  | Description                                 |
|:----------|:------|:--------------------------------------------|
| `title`   | `str` | Specification title (required)              |
| `version` | `str` | Specification version (default: "1.0.0")    |
| `status`  | `str` | One of: draft, review, approved, deprecated |

### User context

Additional variables can be provided by the user when rendering templates.

## Template syntax

### Basic variable substitution

```jinja2
# {{ title }}

Author: {{ author_name }}
Created: {{ today }}
```

### Default values

Use the `or` operator for optional variables:

```jinja2
Author: {{ author_name or "[Author name]" }}
Version: {{ version or "1.0.0" }}
```

### Conditionals

```jinja2
{% if author_name %}
Author: {{ author_name }}
{% endif %}

{% if status == "draft" %}
**Note:** This document is a draft.
{% endif %}
```

### Loops

```jinja2
## Detected Tools

{% for tool, version in tool_versions.items() %}
- {{ tool }}: {{ version }}
{% endfor %}
```

### Filters

Jinja2 filters transform values:

```jinja2
# {{ title | upper }}
Created: {{ today | string }}
Tools: {{ tool_versions | length }} detected
```

## Frontmatter templating

Reference frontmatter values can use templates:

```yaml
---
name: project-setup
title: Project Setup for {{ tool_versions.get('python', 'Python') }}
description: Setup guide for projects using Python {{ tool_versions.get('python', '3.x') }}.
---
```

When the frontmatter is parsed, template variables are rendered with the current context.

### Dynamic frontmatter keys

If a frontmatter key renders to an empty string, the entire entry is removed:

```yaml
---
name: example
{{ "author" if author_name else "" }}: {{ author_name }}
---
```

If `author_name` is not set, the `author` field is omitted entirely.

## Template files (.j2)

Template files use the `.md.j2` extension and live in `templates/`:

```
skill-name/
└── templates/
    ├── lightweight.md.j2
    ├── formal.md.j2
    └── technical.md.j2
```

### Template frontmatter

Template files require frontmatter with `name` and `description`:

```jinja2
---
name: lightweight
description: Simple template for iterative development
---

# {{ title }}

## Overview
...
```

### Nested frontmatter

Templates can generate documents with their own frontmatter:

```jinja2
---
name: formal
description: Full spec with document frontmatter
---
---
title: {{ title }}
version: {{ version }}
status: {{ status }}
author: {{ author_name or "[Author name]" }}
created: {{ today }}
---

# {{ title }}

## Overview
...
```

The outer frontmatter (first `---` block) is template metadata. The inner frontmatter becomes part of the rendered output.

## Context composition

Context is built from multiple layers:

1. **Base context**: `today`, `author_name`, `author_email`, `tool_versions`
2. **Component context**: Additional variables for specific contexts (e.g., `title`, `status` for specs)
3. **User context**: User-provided overrides

Later layers override earlier ones:

```python
# Pseudocode for context composition
context = {}
context.update(base_context)      # today, author_name, etc.
context.update(component_context) # title, version, etc.
context.update(user_context)      # user overrides
```

## Examples

### Reference with tool version

```jinja2
---
name: python-setup
title: Python {{ tool_versions.get('python', '3.x') }} Setup
description: Setup guide for Python projects.
---

## Python Version

This project uses Python {{ tool_versions.get('python', '3.x') }}.

{% if tool_versions.get('uv') %}
## Package Manager

This project uses uv {{ tool_versions.get('uv') }} for package management.
{% endif %}
```

### Workflow with conditional steps

```jinja2
---
name: test-workflow
description: Run tests for the project
default: true
---

## Running Tests

1. Ensure dependencies are installed

{% if tool_versions.get('uv') %}
2. Run tests with uv:
   ```bash
   uv run pytest
   ```

{% else %}
2. Run tests with pytest:

   ```bash
   pytest
   ```

{% endif %}

3. Verify all tests pass

```

### Specification template

```jinja2
---
name: feature
description: Feature specification template
---
---
title: {{ title }}
version: {{ version }}
status: {{ status }}
author: {{ author_name or "[Author name]" }}
created: {{ today }}
---

# Feature: {{ title }}

## Status

| Field   | Value                      |
|:--------|:---------------------------|
| Version | {{ version }}              |
| Status  | {{ status }}               |
| Author  | {{ author_name or "TBD" }} |
| Created | {{ today }}                |

## Overview

Brief description of what this feature does.

## Requirements

- [ ] Requirement 1
- [ ] Requirement 2
```

## Template discovery

Templates are discovered from two locations with override support:

1. **Override location**: `.oaps/overrides/skills/<skill>/templates/`
2. **Builtin location**: `skills/<skill>/templates/`

Override templates take precedence over builtin templates with the same name.
