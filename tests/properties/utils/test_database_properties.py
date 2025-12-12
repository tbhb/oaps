import pytest
from hypothesis import given, strategies as st

from oaps.utils.database import safe_identifier

# Valid SQL identifiers: start with letter/underscore, then alphanumeric/underscore
valid_identifier = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]*", fullmatch=True)

# Characters that would enable SQL injection
INJECTION_CHARS = frozenset("'\";-/*\\")


@given(name=valid_identifier)
def test_safe_identifier_accepts_all_valid_identifiers(name: str) -> None:
    result = safe_identifier(name)
    assert result == f'"{name}"'


@given(name=st.text())
def test_safe_identifier_output_is_always_quoted(name: str) -> None:
    try:
        result = safe_identifier(name)
        assert result.startswith('"')
        assert result.endswith('"')
    except ValueError:
        pass


@given(
    prefix=st.text(min_size=0, max_size=10),
    injection_char=st.sampled_from(list(INJECTION_CHARS)),
    suffix=st.text(min_size=0, max_size=10),
)
def test_safe_identifier_rejects_injection_characters(
    prefix: str, injection_char: str, suffix: str
) -> None:
    name = prefix + injection_char + suffix
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        _ = safe_identifier(name)


@given(name=st.text(alphabet=st.characters(categories=["Nd"]), min_size=1))
def test_safe_identifier_rejects_leading_digits(name: str) -> None:
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        _ = safe_identifier(name)


def test_safe_identifier_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        _ = safe_identifier("")


@given(
    prefix=st.text(alphabet=st.characters(categories=["L", "Nd", "Pc"]), min_size=0),
    whitespace=st.text(alphabet=st.characters(whitelist_categories=["Zs"]), min_size=1),
    suffix=st.text(alphabet=st.characters(categories=["L", "Nd", "Pc"]), min_size=0),
)
def test_safe_identifier_rejects_whitespace(
    prefix: str, whitespace: str, suffix: str
) -> None:
    name = prefix + whitespace + suffix
    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        _ = safe_identifier(name)
