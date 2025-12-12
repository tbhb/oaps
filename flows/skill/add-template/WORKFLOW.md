---
description: Add a new template to a skill
---

## Add template

### Step 1: Determine template need

Identify what the template should generate:

- What output does this template produce?
- What variables need to be substituted?
- Is this for Jinja2 rendering or static content?

Common template types:

- **Jinja2 templates** (`.j2` extension): Dynamic content with variable substitution
- **Static templates** (`.md`, `.txt`, etc.): Fixed content to copy and customize

### Step 2: Choose template name

Select a descriptive name:

- For Jinja2 templates: `<name>.md.j2`, `<name>.txt.j2`
- For static templates: `<name>.md`, `<name>.txt`
- Be specific: `skill-template.md.j2` not just `template.md.j2`

### Step 3: Create template file

Create the file in the skill's templates directory:

```bash
mkdir -p <skill-path>/templates/
touch <skill-path>/templates/<name>
```

### Step 4: Write template content

For Jinja2 templates, use Jinja2 syntax:

```jinja
---
name: {{ name }}
description: {{ description }}
version: {{ version | default('0.1.0') }}
---

# {{ title }}

{{ content }}

{% if examples %}
## Examples

{% for example in examples %}
- {{ example }}
{% endfor %}
{% endif %}
```

**Available context variables:**

- Base context: `project_name`, `project_root`, `skill_name`, `skill_path`
- Skill context: `references`, `workflows`, `templates`
- User context: Variables passed via CLI or skill invocation

### Step 5: Test template rendering

If using Jinja2, test the template renders correctly:

```bash
oaps skill render <skill-name> --template <template-name> --var key=value
```

### Step 6: Document usage

Update relevant workflows or references to document:

- When to use this template
- Required variables
- Expected output

### Step 7: Validate

Run validation:

```bash
oaps skill validate <skill-name>
```

### Step 8: Commit

Save the changes:

```bash
oaps skill save --message "add template: <name>" <skill-name>
```
