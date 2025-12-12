from oaps.templating import render_braces_template, render_template_string


class TestRenderBracesTemplate:
    def test_single_variable_substitution(self):
        result = render_braces_template("Hello {name}", {"name": "World"})
        assert result == "Hello World"

    def test_multiple_variable_substitution(self):
        result = render_braces_template(
            "{greeting} {name}!", {"greeting": "Hello", "name": "World"}
        )
        assert result == "Hello World!"

    def test_no_variables_returns_unchanged(self):
        result = render_braces_template("static text", {"name": "unused"})
        assert result == "static text"


class TestRenderJinjaTemplate:
    def test_single_variable_substitution(self):
        result = render_template_string("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_multiple_variable_substitution(self):
        result = render_template_string(
            "{{ greeting }} {{ name }}!", {"greeting": "Hello", "name": "World"}
        )
        assert result == "Hello World!"

    def test_no_variables_returns_unchanged(self):
        result = render_template_string("static text", {"name": "unused"})
        assert result == "static text"

    def test_empty_string_returns_empty(self):
        result = render_template_string("", {"name": "test"})
        assert result == ""

    def test_empty_context_with_no_variables(self):
        result = render_template_string("no variables", {})
        assert result == "no variables"

    def test_non_string_value_renders(self):
        result = render_template_string("count: {{ n }}", {"n": 42})
        assert result == "count: 42"

    def test_missing_variable_renders_empty(self):
        result = render_template_string("{{ missing }}", {"other": "value"})
        assert result == ""

    def test_filter_usage(self):
        result = render_template_string("{{ name|upper }}", {"name": "world"})
        assert result == "WORLD"

    def test_conditional_rendering(self):
        template = "{% if show %}visible{% endif %}"
        assert render_template_string(template, {"show": True}) == "visible"
        assert render_template_string(template, {"show": False}) == ""

    def test_loop_rendering(self):
        template = "{% for item in items %}{{ item }} {% endfor %}"
        result = render_template_string(template, {"items": ["a", "b", "c"]})
        assert result == "a b c "

    def test_default_filter_for_missing_variable(self):
        result = render_template_string(
            "{{ missing|default('fallback') }}", {"other": "value"}
        )
        assert result == "fallback"

    def test_whitespace_control(self):
        template = "{%- if True -%}no whitespace{%- endif -%}"
        result = render_template_string(template, {})
        assert result == "no whitespace"
