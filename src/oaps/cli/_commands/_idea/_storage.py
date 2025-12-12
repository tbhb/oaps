# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false, reportUnknownMemberType=false
"""Storage functions for idea documents."""

import re
from typing import TYPE_CHECKING, Any

import pendulum

from oaps.spec._io import read_markdown_frontmatter, write_markdown_with_frontmatter
from oaps.utils._paths import get_oaps_dir

from ._models import (
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaReference,
    IdeaStatus,
    IdeaType,
    IdeaWorkflowState,
)

if TYPE_CHECKING:
    from pathlib import Path


def get_ideas_dir() -> Path:
    """Get the ideas directory path.

    Returns:
        Path to .oaps/docs/ideas/
    """
    return get_oaps_dir() / "docs" / "ideas"


def generate_idea_id(title: str) -> str:
    """Generate a unique idea ID from timestamp and title slug.

    Args:
        title: The idea title.

    Returns:
        ID in format YYYYMMDD-HHMMSS-slug
    """
    now = pendulum.now("UTC")
    timestamp = now.format("YYYYMMDD-HHmmss")
    slug = slugify(title)
    return f"{timestamp}-{slug}"


def slugify(text: str) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to slugify.

    Returns:
        Lowercase slug with hyphens.
    """
    # Lowercase and replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)
    # Limit length
    return slug[:50]


def idea_filename(idea_id: str) -> str:
    """Generate filename from idea ID.

    Args:
        idea_id: The idea ID.

    Returns:
        Filename with .md extension.
    """
    return f"{idea_id}.md"


def parse_idea_frontmatter(data: dict[str, Any]) -> IdeaFrontmatter:
    """Parse raw frontmatter dict into IdeaFrontmatter.

    Args:
        data: Raw frontmatter dictionary.

    Returns:
        Parsed IdeaFrontmatter instance.
    """
    # Parse workflow state if present
    workflow: IdeaWorkflowState | None = None
    if "workflow" in data and isinstance(data["workflow"], dict):
        workflow_data: dict[str, Any] = data["workflow"]
        workflow = IdeaWorkflowState(
            phase=str(workflow_data.get("phase", "")),
            iteration=int(workflow_data.get("iteration", 0)),
        )

    # Parse references
    refs: list[IdeaReference] = []
    if "references" in data and isinstance(data["references"], list):
        refs.extend(
            IdeaReference(url=str(ref.get("url", "")), title=str(ref.get("title", "")))
            for ref in data["references"]
            if isinstance(ref, dict)
        )

    return IdeaFrontmatter(
        id=str(data.get("id", "")),
        title=str(data.get("title", "")),
        status=IdeaStatus(str(data.get("status", "seed"))),
        type=IdeaType(str(data.get("type", "technical"))),
        created=str(data.get("created", "")),
        updated=str(data.get("updated", "")),
        author=data.get("author"),
        tags=tuple(str(t) for t in data.get("tags", [])),
        related_ideas=tuple(str(r) for r in data.get("related_ideas", [])),
        references=tuple(refs),
        workflow=workflow,
    )


def load_idea(path: Path) -> tuple[IdeaFrontmatter, str]:
    """Load an idea document.

    Args:
        path: Path to the idea markdown file.

    Returns:
        Tuple of (frontmatter, body content).

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If frontmatter is invalid.
    """
    frontmatter, body = read_markdown_frontmatter(path)
    if not frontmatter:
        msg = f"No frontmatter found in {path}"
        raise ValueError(msg)

    return parse_idea_frontmatter(frontmatter), body


def frontmatter_to_dict(fm: IdeaFrontmatter) -> dict[str, Any]:
    """Convert IdeaFrontmatter to dict for serialization.

    Args:
        fm: The frontmatter object.

    Returns:
        Dictionary suitable for YAML serialization.
    """
    result: dict[str, Any] = {
        "id": fm.id,
        "title": fm.title,
        "status": fm.status.value,
        "type": fm.type.value,
        "created": fm.created,
        "updated": fm.updated,
        "tags": list(fm.tags),
        "related_ideas": list(fm.related_ideas),
        "references": [dict(r) for r in fm.references],
    }
    if fm.author:
        result["author"] = fm.author
    if fm.workflow:
        result["workflow"] = dict(fm.workflow)
    return result


def save_idea(path: Path, frontmatter: IdeaFrontmatter, body: str) -> None:
    """Save an idea document.

    Args:
        path: Path to save the file.
        frontmatter: The frontmatter data.
        body: The markdown body content.
    """
    fm_dict = frontmatter_to_dict(frontmatter)
    write_markdown_with_frontmatter(path, fm_dict, body)


def load_index() -> list[IdeaIndexEntry]:
    """Load the ideas index.

    Returns:
        List of index entries. Empty list if index doesn't exist.
    """
    import orjson

    index_path = get_ideas_dir() / "index.json"
    if not index_path.exists():
        return []

    content = index_path.read_bytes()
    data: dict[str, Any] = orjson.loads(content)

    ideas_list: list[dict[str, Any]] = data.get("ideas", [])
    return [
        IdeaIndexEntry(
            id=str(item["id"]),
            title=str(item["title"]),
            status=str(item["status"]),
            type=str(item["type"]),
            tags=tuple(str(t) for t in item.get("tags", [])),
            file_path=str(item["file_path"]),
            created=str(item["created"]),
            updated=str(item["updated"]),
            author=item.get("author"),
        )
        for item in ideas_list
    ]


def save_index(entries: list[IdeaIndexEntry]) -> None:
    """Save the ideas index.

    Args:
        entries: List of index entries to save.
    """
    import orjson

    ideas_dir = get_ideas_dir()
    _ = ideas_dir.mkdir(parents=True, exist_ok=True)
    index_path = ideas_dir / "index.json"

    now = pendulum.now("UTC").to_iso8601_string()
    data = {
        "updated": now,
        "ideas": [
            {
                "id": e.id,
                "title": e.title,
                "status": e.status,
                "type": e.type,
                "tags": list(e.tags),
                "file_path": e.file_path,
                "created": e.created,
                "updated": e.updated,
                "author": e.author,
            }
            for e in entries
        ],
    }

    content = orjson.dumps(data, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
    _ = index_path.write_bytes(content)


def rebuild_index() -> list[IdeaIndexEntry]:
    """Rebuild index from filesystem.

    Scans all .md files in ideas directory and rebuilds the index.

    Returns:
        List of all discovered index entries.
    """
    ideas_dir = get_ideas_dir()
    if not ideas_dir.exists():
        return []

    entries: list[IdeaIndexEntry] = []
    for path in sorted(ideas_dir.glob("*.md")):
        try:
            fm, _ = load_idea(path)
            entries.append(
                IdeaIndexEntry(
                    id=fm.id,
                    title=fm.title,
                    status=fm.status.value,
                    type=fm.type.value,
                    tags=fm.tags,
                    file_path=path.name,
                    created=fm.created,
                    updated=fm.updated,
                    author=fm.author,
                )
            )
        except (ValueError, FileNotFoundError):
            continue

    save_index(entries)
    return entries


def find_idea_by_id(idea_id: str) -> Path | None:
    """Find idea file by ID.

    Args:
        idea_id: The idea ID to find.

    Returns:
        Path to the idea file, or None if not found.
    """
    ideas_dir = get_ideas_dir()

    # Try exact filename match first
    exact_path = ideas_dir / f"{idea_id}.md"
    if exact_path.exists():
        return exact_path

    # Search through index
    for entry in load_index():
        if entry.id == idea_id:
            return ideas_dir / entry.file_path

    # Fallback: search files by ID prefix
    for path in ideas_dir.glob("*.md"):
        try:
            fm, _ = load_idea(path)
            if fm.id == idea_id:
                return path
        except (ValueError, FileNotFoundError):
            continue

    return None
