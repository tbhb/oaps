"""Property-based tests for artifact store operations."""

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from oaps.artifacts._registry import ArtifactRegistry
from oaps.artifacts._store import ArtifactStore

# =============================================================================
# Strategies
# =============================================================================

# Valid type prefixes from base types (exclude CH - has required change_type field)
valid_prefix = st.sampled_from(["DC", "AN", "RP", "EX"])

# Safe titles (no YAML-breaking characters)
safe_title = st.text(
    alphabet=st.characters(
        whitelist_categories=["L", "N", "Zs"],
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() and not x.startswith("-"))

# Safe author names
safe_author = st.text(
    alphabet=st.characters(whitelist_categories=["L", "N"], whitelist_characters="-_"),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip())

# Safe body content
safe_body = st.text(
    alphabet=st.characters(whitelist_categories=["L", "N", "Zs", "P"]),
    min_size=0,
    max_size=200,
)


def create_store() -> tuple[ArtifactStore, tempfile.TemporaryDirectory[str]]:
    """Create a fresh store with a temporary directory."""
    ArtifactRegistry._reset_instance()
    tmpdir = tempfile.TemporaryDirectory()
    store = ArtifactStore(Path(tmpdir.name))
    store.initialize()
    return store, tmpdir


# =============================================================================
# Add/Get Properties
# =============================================================================


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=30)
def test_get_after_add_returns_artifact(prefix: str, title: str, author: str) -> None:
    """Property: get_artifact after add_artifact returns the artifact."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )

        retrieved = store.get_artifact(artifact.id)

        assert retrieved is not None
        assert retrieved.id == artifact.id
        assert retrieved.title == title
        assert retrieved.author == author
    finally:
        tmpdir.cleanup()


@given(prefix=valid_prefix, title=safe_title, author=safe_author, content=safe_body)
@settings(max_examples=30)
def test_content_preserved_after_add(
    prefix: str, title: str, author: str, content: str
) -> None:
    """Property: artifact content is preserved after adding."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
            content=content,
        )

        retrieved_content = store.get_artifact_content(artifact.id)
        assert retrieved_content is not None
        assert isinstance(retrieved_content, str)
        # Content may have trailing whitespace stripped by YAML, so use strip()
        assert content.strip() in retrieved_content
    finally:
        tmpdir.cleanup()


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=30)
def test_artifact_exists_after_add(prefix: str, title: str, author: str) -> None:
    """Property: artifact_exists returns True after add_artifact."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )

        assert store.artifact_exists(artifact.id)
    finally:
        tmpdir.cleanup()


# =============================================================================
# Sequential Number Properties
# =============================================================================


@given(prefix=valid_prefix, count=st.integers(min_value=1, max_value=10))
@settings(max_examples=20)
def test_sequential_ids_are_unique(prefix: str, count: int) -> None:
    """Property: multiple artifacts of same type have sequential unique IDs."""
    store, tmpdir = create_store()
    try:
        ids = []
        for i in range(count):
            artifact = store.add_artifact(
                type_prefix=prefix,
                title=f"Artifact {i}",
                author="test",
            )
            ids.append(artifact.id)

        # All IDs should be unique
        assert len(ids) == len(set(ids))

        # All IDs should start with the prefix
        assert all(id_.startswith(f"{prefix}-") for id_ in ids)
    finally:
        tmpdir.cleanup()


@given(prefix=valid_prefix, count=st.integers(min_value=2, max_value=5))
@settings(max_examples=15)
def test_ids_are_sequential(prefix: str, count: int) -> None:
    """Property: artifact numbers are sequential within type."""
    store, tmpdir = create_store()
    try:
        numbers = []
        for i in range(count):
            artifact = store.add_artifact(
                type_prefix=prefix,
                title=f"Artifact {i}",
                author="test",
            )
            numbers.append(artifact.number)

        # Numbers should be 1, 2, 3, ...
        expected = list(range(1, count + 1))
        assert numbers == expected
    finally:
        tmpdir.cleanup()


# =============================================================================
# Index Consistency Properties
# =============================================================================


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=20)
def test_index_count_increases_after_add(prefix: str, title: str, author: str) -> None:
    """Property: index count increases by 1 after adding artifact."""
    store, tmpdir = create_store()
    try:
        initial_count = store.get_index().count

        store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )

        assert store.get_index().count == initial_count + 1
    finally:
        tmpdir.cleanup()


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=20)
def test_index_contains_added_artifact(prefix: str, title: str, author: str) -> None:
    """Property: index contains artifact after adding."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )

        index = store.get_index()
        assert index.contains(artifact.id)

        summary = index.get(artifact.id)
        assert summary is not None
        assert summary["title"] == title
    finally:
        tmpdir.cleanup()


# =============================================================================
# Delete Properties
# =============================================================================


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=20)
def test_artifact_not_exists_after_delete(prefix: str, title: str, author: str) -> None:
    """Property: artifact_exists returns False after deletion."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )
        artifact_id = artifact.id

        store.delete_artifact(artifact_id, force=True)

        assert not store.artifact_exists(artifact_id)
    finally:
        tmpdir.cleanup()


@given(prefix=valid_prefix, title=safe_title, author=safe_author)
@settings(max_examples=20)
def test_index_count_decreases_after_delete(
    prefix: str, title: str, author: str
) -> None:
    """Property: index count decreases by 1 after deletion."""
    store, tmpdir = create_store()
    try:
        artifact = store.add_artifact(
            type_prefix=prefix,
            title=title,
            author=author,
        )

        count_before = store.get_index().count

        store.delete_artifact(artifact.id, force=True)

        assert store.get_index().count == count_before - 1
    finally:
        tmpdir.cleanup()
