---
description: Update an existing template
---

## Update template

### Step 1: Read the template

Read the complete template file:

- Understand its current structure and variables
- Note if it's a Jinja2 template (`.j2`) or static template
- Identify what output it produces

### Step 2: Identify changes needed

Determine what needs to be updated:

- **Variable changes**: new variables, removed variables, renamed variables
- **Content changes**: updated text, new sections, formatting
- **Structural changes**: reorganization, conditional sections

### Step 3: Update template content

Apply changes to the template:

- Maintain consistent Jinja2 syntax if applicable
- Use default values for optional variables: `{{ var | default('default') }}`
- Add conditionals for optional sections: `{% if condition %}...{% endif %}`

### Step 4: Test template rendering

For Jinja2 templates, test with sample values:

```bash
oaps skill render <skill-name> --template <template-name> --var key=value
```

Verify:

- All variables are substituted correctly
- Conditionals work as expected
- Output format is correct

### Step 5: Update documentation

If the template's variables or usage changed:

1. Update relevant workflows that use this template
1. Update references that document this template
1. Ensure variable documentation is current

### Step 6: Validate

Run validation:

```bash
oaps skill validate <skill-name>
```

### Step 7: Commit

Save the changes:

```bash
oaps skill save --message "update template: <name>" <skill-name>
```
