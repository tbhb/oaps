# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# ruff: noqa: A002, D415, FBT002, PLR2004
"""Idea management commands."""

import sys
from dataclasses import replace
from typing import Annotated

import pendulum
from cyclopts import Parameter
from pytablewriter import MarkdownTableWriter
from rich.console import Console

from oaps.cli._commands._context import CLIContext

# Re-export app
from ._app import app

# Export models and storage for other modules
from ._models import (
    STATUS_EMOJI,
    IdeaFrontmatter,
    IdeaIndexEntry,
    IdeaStatus,
    IdeaType,
)
from ._storage import (
    find_idea_by_id,
    generate_idea_id,
    get_ideas_dir,
    idea_filename,
    load_idea,
    load_index,
    rebuild_index,
    save_idea,
    save_index,
)

__all__ = [
    "STATUS_EMOJI",
    "IdeaFrontmatter",
    "IdeaIndexEntry",
    "IdeaStatus",
    "IdeaType",
    "app",
    "find_idea_by_id",
    "generate_idea_id",
    "get_ideas_dir",
    "idea_filename",
    "load_idea",
    "load_index",
    "rebuild_index",
    "save_idea",
    "save_index",
]

# Template for idea body
IDEA_BODY_TEMPLATE = """<!-- idea-header-start -->
{status_emoji} **{status}** | {type} | {tags_display}
<!-- idea-header-end -->

# {title}

## Core Concept

*What is the central idea?*

## Context

*Why is this idea relevant now?*

## Questions to Explore

-{space}

## Initial Observations


<!-- idea-footer-start -->
---
**References**: None yet
**Related Ideas**: None yet
<!-- idea-footer-end -->
"""


def _format_tags_display(tags: tuple[str, ...] | list[str]) -> str:
    """Format tags for display.

    Args:
        tags: List of tag names.

    Returns:
        Formatted tags string with hashtags.
    """
    if not tags:
        return "*no tags*"
    return " ".join(f"#{tag}" for tag in tags)


@app.command(name="create")
def _create(
    title: str,
    /,
    type: Annotated[
        str,
        Parameter(
            name=["--type", "-t"],
            help="Idea type (technical, product, process, research)",
        ),
    ] = "technical",
    tags: Annotated[
        list[str] | None, Parameter(name=["--tags"], help="Tags for the idea")
    ] = None,
) -> None:
    """Create a new idea document

    Creates an idea document in .oaps/docs/ideas/ with the given title.
    """
    console = Console()

    # Validate type
    try:
        idea_type = IdeaType(type)
    except ValueError:
        valid_types = ", ".join(t.value for t in IdeaType)
        console.print(f"[red]Error:[/red] Invalid type '{type}'. Valid: {valid_types}")
        sys.exit(1)

    # Generate ID and timestamps
    idea_id = generate_idea_id(title)
    now = pendulum.now("UTC")
    timestamp = now.to_iso8601_string()

    # Create frontmatter
    tags_tuple = tuple(tags) if tags else ()
    frontmatter = IdeaFrontmatter(
        id=idea_id,
        title=title,
        status=IdeaStatus.SEED,
        type=idea_type,
        created=timestamp,
        updated=timestamp,
        tags=tags_tuple,
    )

    # Create body
    tags_display = _format_tags_display(tags_tuple)
    body = IDEA_BODY_TEMPLATE.format(
        status_emoji=STATUS_EMOJI[IdeaStatus.SEED],
        status=IdeaStatus.SEED.value,
        type=idea_type.value,
        tags_display=tags_display,
        title=title,
        space=" ",  # Prevents trailing whitespace removal
    )

    # Ensure directory exists and save
    ideas_dir = get_ideas_dir()
    _ = ideas_dir.mkdir(parents=True, exist_ok=True)
    file_path = ideas_dir / idea_filename(idea_id)
    save_idea(file_path, frontmatter, body)

    # Update index
    index = load_index()
    entry = IdeaIndexEntry(
        id=idea_id,
        title=title,
        status=IdeaStatus.SEED.value,
        type=idea_type.value,
        tags=tags_tuple,
        file_path=idea_filename(idea_id),
        created=timestamp,
        updated=timestamp,
    )
    index.append(entry)
    save_index(index)

    console.print(f"[green]Created idea:[/green] {file_path}")


@app.command(name="list")
def _list(
    status: Annotated[
        str | None, Parameter(name=["--status", "-s"], help="Filter by status")
    ] = None,
    tag: Annotated[str | None, Parameter(name=["--tag"], help="Filter by tag")] = None,
    type: Annotated[
        str | None, Parameter(name=["--type", "-t"], help="Filter by type")
    ] = None,
    limit: Annotated[
        int, Parameter(name=["--limit", "-n"], help="Maximum number to show")
    ] = 20,
) -> None:
    """List ideas with optional filtering"""
    console = Console()

    # Validate filter parameters
    if status:
        try:
            _ = IdeaStatus(status)
        except ValueError:
            valid = ", ".join(s.value for s in IdeaStatus)
            console.print(
                f"[red]Error:[/red] Invalid status '{status}'. Valid: {valid}"
            )
            sys.exit(1)

    if type:
        try:
            _ = IdeaType(type)
        except ValueError:
            valid = ", ".join(t.value for t in IdeaType)
            console.print(f"[red]Error:[/red] Invalid type '{type}'. Valid: {valid}")
            sys.exit(1)

    index = load_index()

    if not index:
        console.print("[dim]No ideas found.[/dim]")
        return

    # Apply filters
    filtered = index

    if status:
        filtered = [e for e in filtered if e.status == status]

    if tag:
        filtered = [e for e in filtered if tag in e.tags]

    if type:
        filtered = [e for e in filtered if e.type == type]

    # Sort by updated (most recent first) and limit
    filtered = sorted(filtered, key=lambda e: e.updated, reverse=True)[:limit]

    if not filtered:
        console.print("[dim]No ideas match the filters.[/dim]")
        return

    # Build table rows with safe status emoji lookup
    def get_status_emoji(status: str) -> str:
        try:
            status_enum = IdeaStatus(status)
            return STATUS_EMOJI.get(status_enum, "?")
        except ValueError:
            return "?"

    writer = MarkdownTableWriter(
        headers=["Status", "ID", "Title", "Type", "Tags"],
        value_matrix=[
            [
                get_status_emoji(e.status),
                e.id,  # Full ID - never truncate
                e.title[:30] + "..." if len(e.title) > 33 else e.title,
                e.type,
                ", ".join(e.tags[:3]) + ("..." if len(e.tags) > 3 else ""),
            ]
            for e in filtered
        ],
        margin=1,
    )

    console.print(writer.dumps())
    console.print(f"\n[dim]Showing {len(filtered)} of {len(index)} ideas[/dim]")
    console.print("[dim]To view an idea: oaps idea show <full-id>[/dim]")


@app.command(name="show")
def _show(idea_id: str, /) -> None:
    """Display an idea document"""
    console = Console()

    path = find_idea_by_id(idea_id)
    if path is None:
        console.print(f"[red]Error:[/red] Idea not found: {idea_id}")
        sys.exit(1)

    try:
        frontmatter, body = load_idea(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Print frontmatter summary
    console.print(f"[bold]{frontmatter.title}[/bold]")
    status_line = (
        f"{STATUS_EMOJI[frontmatter.status]} {frontmatter.status.value} | "
        f"{frontmatter.type.value} | {_format_tags_display(frontmatter.tags)}"
    )
    console.print(status_line)
    console.print(f"[dim]ID: {frontmatter.id}[/dim]")
    console.print(f"[dim]Created: {frontmatter.created}[/dim]")
    console.print(f"[dim]Updated: {frontmatter.updated}[/dim]")

    if frontmatter.related_ideas:
        console.print(f"[dim]Related: {', '.join(frontmatter.related_ideas)}[/dim]")

    console.print("\n---\n")
    console.print(body)


@app.command(name="search")
def _search(query: str, /) -> None:
    """Search ideas by content"""
    console = Console()
    ideas_dir = get_ideas_dir()

    if not ideas_dir.exists():
        console.print("[dim]No ideas found.[/dim]")
        return

    query_lower = query.lower()
    results: list[tuple[IdeaFrontmatter, str]] = []

    for path in ideas_dir.glob("*.md"):
        try:
            fm, body = load_idea(path)
            # Search in title, body, and tags
            if (
                query_lower in fm.title.lower()
                or query_lower in body.lower()
                or any(query_lower in tag.lower() for tag in fm.tags)
            ):
                results.append((fm, path.name))
        except (ValueError, FileNotFoundError):
            continue

    if not results:
        console.print(f"[dim]No ideas match '{query}'.[/dim]")
        return

    console.print(f"[bold]Found {len(results)} idea(s) matching '{query}':[/bold]\n")

    for fm, _ in results:
        console.print(f"  {STATUS_EMOJI[fm.status]} [bold]{fm.title}[/bold]")
        console.print(f"    [dim]ID: {fm.id}[/dim]")
        console.print(
            f"    [dim]{fm.type.value} | {_format_tags_display(fm.tags)}[/dim]"
        )

    console.print("\n[dim]To view an idea: oaps idea show <id>[/dim]")


@app.command(name="archive")
def _archive(idea_id: str, /) -> None:
    """Archive an idea (set status to archived)"""
    console = Console()

    path = find_idea_by_id(idea_id)
    if path is None:
        console.print(f"[red]Error:[/red] Idea not found: {idea_id}")
        sys.exit(1)

    try:
        frontmatter, body = load_idea(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    if frontmatter.status == IdeaStatus.ARCHIVED:
        console.print("[yellow]Idea is already archived.[/yellow]")
        return

    # Update frontmatter
    now = pendulum.now("UTC").to_iso8601_string()
    new_frontmatter = replace(
        frontmatter,
        status=IdeaStatus.ARCHIVED,
        updated=now,
    )

    # Update body header
    new_body = _update_idea_header(body, new_frontmatter)

    save_idea(path, new_frontmatter, new_body)

    # Update index
    _update_index_entry(new_frontmatter)

    console.print(f"[green]Archived idea:[/green] {idea_id}")


@app.command(name="link")
def _link(idea_id: str, related_id: str, /) -> None:
    """Link two ideas as related"""
    console = Console()

    # Find both ideas
    path1 = find_idea_by_id(idea_id)
    path2 = find_idea_by_id(related_id)

    if path1 is None:
        console.print(f"[red]Error:[/red] Idea not found: {idea_id}")
        sys.exit(1)

    if path2 is None:
        console.print(f"[red]Error:[/red] Related idea not found: {related_id}")
        sys.exit(1)

    try:
        fm1, body1 = load_idea(path1)
        fm2, body2 = load_idea(path2)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    now = pendulum.now("UTC").to_iso8601_string()

    # Add link to first idea (if not already linked)
    if fm2.id not in fm1.related_ideas:
        new_related1 = (*fm1.related_ideas, fm2.id)
        new_fm1 = replace(fm1, related_ideas=new_related1, updated=now)
        new_body1 = _update_idea_footer(body1, new_fm1)
        save_idea(path1, new_fm1, new_body1)

    # Add link to second idea (if not already linked)
    if fm1.id not in fm2.related_ideas:
        new_related2 = (*fm2.related_ideas, fm1.id)
        new_fm2 = replace(fm2, related_ideas=new_related2, updated=now)
        new_body2 = _update_idea_footer(body2, new_fm2)
        save_idea(path2, new_fm2, new_body2)

    console.print(f"[green]Linked ideas:[/green] {idea_id} <-> {related_id}")


@app.command(name="unlink")
def _unlink(idea_id: str, related_id: str, /) -> None:
    """Remove relationship between ideas"""
    console = Console()

    # Find both ideas
    path1 = find_idea_by_id(idea_id)
    path2 = find_idea_by_id(related_id)

    if path1 is None:
        console.print(f"[red]Error:[/red] Idea not found: {idea_id}")
        sys.exit(1)

    if path2 is None:
        console.print(f"[red]Error:[/red] Related idea not found: {related_id}")
        sys.exit(1)

    try:
        fm1, body1 = load_idea(path1)
        fm2, body2 = load_idea(path2)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    now = pendulum.now("UTC").to_iso8601_string()

    # Remove link from first idea
    if fm2.id in fm1.related_ideas:
        new_related1 = tuple(r for r in fm1.related_ideas if r != fm2.id)
        new_fm1 = replace(fm1, related_ideas=new_related1, updated=now)
        new_body1 = _update_idea_footer(body1, new_fm1)
        save_idea(path1, new_fm1, new_body1)

    # Remove link from second idea
    if fm1.id in fm2.related_ideas:
        new_related2 = tuple(r for r in fm2.related_ideas if r != fm1.id)
        new_fm2 = replace(fm2, related_ideas=new_related2, updated=now)
        new_body2 = _update_idea_footer(body2, new_fm2)
        save_idea(path2, new_fm2, new_body2)

    console.print(f"[green]Unlinked ideas:[/green] {idea_id} <-> {related_id}")


@app.command(name="tags")
def _tags(
    show_usage: Annotated[
        bool, Parameter(name=["--usage", "-u"], help="Show usage counts")
    ] = False,
) -> None:
    """List available tags with descriptions"""
    console = Console()
    ctx = CLIContext.get_current()
    all_tags = ctx.config.ideas.all_tags

    if not all_tags:
        console.print("[dim]No tags configured.[/dim]")
        return

    # Count usage if requested
    usage_counts: dict[str, int] = {}
    if show_usage:
        index = load_index()
        for entry in index:
            for tag in entry.tags:
                usage_counts[tag] = usage_counts.get(tag, 0) + 1

    # Build table
    headers = ["Tag", "Description"]
    if show_usage:
        headers.append("Usage")

    rows: list[list[str]] = []
    for tag_name, description in sorted(all_tags.items()):
        row = [f"#{tag_name}", description]
        if show_usage:
            row.append(str(usage_counts.get(tag_name, 0)))
        rows.append(row)

    writer = MarkdownTableWriter(
        headers=headers,
        value_matrix=rows,
        margin=1,
    )

    console.print(writer.dumps())


@app.command(name="tag-add")
def _tag_add(name: str, description: str, /) -> None:
    """Add a tag to project configuration (extend_tags)

    Note: This prints instructions for adding to configuration manually.
    """
    console = Console()

    console.print("[bold]To add this tag, update your OAPS configuration:[/bold]\n")
    console.print("Add to .oaps/config/oaps.toml:\n")
    console.print("[ideas]")
    console.print("[ideas.extend_tags]")
    console.print(f'{name} = "{description}"')
    console.print()
    env_var_msg = (
        "[dim]Or use environment variable:[/dim] "
        f'OAPS_IDEAS_EXTEND_TAGS_{name.upper()}="{description}"'
    )
    console.print(env_var_msg)


@app.command(name="tag-describe")
def _tag_describe(name: str, /) -> None:
    """Show tag details and usage"""
    console = Console()
    ctx = CLIContext.get_current()
    all_tags = ctx.config.ideas.all_tags

    if name not in all_tags:
        console.print(f"[red]Error:[/red] Tag '{name}' not found in configuration.")
        console.print("[dim]Run `oaps idea tags` to see available tags.[/dim]")
        sys.exit(1)

    description = all_tags[name]

    # Count usage
    index = load_index()
    ideas_with_tag = [e for e in index if name in e.tags]

    console.print(f"[bold]#{name}[/bold]")
    console.print(f"Description: {description}")
    console.print(f"Used by: {len(ideas_with_tag)} idea(s)")

    if ideas_with_tag:
        console.print("\n[bold]Ideas with this tag:[/bold]")
        for entry in ideas_with_tag[:10]:
            status_emoji = STATUS_EMOJI.get(IdeaStatus(entry.status), "?")
            console.print(f"  {status_emoji} {entry.title}")
            console.print(f"      [dim]ID: {entry.id}[/dim]")
        if len(ideas_with_tag) > 10:
            console.print(f"  [dim]... and {len(ideas_with_tag) - 10} more[/dim]")
        console.print("\n[dim]To view an idea: oaps idea show <id>[/dim]")


@app.command(name="sync-headers")
def _sync_headers() -> None:
    """Regenerate all idea document headers/footers from frontmatter"""
    console = Console()
    ideas_dir = get_ideas_dir()

    if not ideas_dir.exists():
        console.print("[dim]No ideas directory found.[/dim]")
        return

    updated = 0
    errors = 0

    for path in ideas_dir.glob("*.md"):
        try:
            fm, body = load_idea(path)
            new_body = _update_idea_header(body, fm)
            new_body = _update_idea_footer(new_body, fm)
            save_idea(path, fm, new_body)
            updated += 1
        except (ValueError, FileNotFoundError) as e:
            console.print(f"[yellow]Warning:[/yellow] {path.name}: {e}")
            errors += 1

    console.print(f"[green]Updated {updated} idea(s).[/green]")
    if errors:
        console.print(f"[yellow]Errors: {errors}[/yellow]")


@app.command(name="resume")
def _resume(idea_id: Annotated[str | None, Parameter()] = None, /) -> None:
    """Show current state summary for resuming work on an idea

    If no idea_id is provided, shows the most recently updated non-archived idea.
    """
    console = Console()

    if idea_id is None:
        # Find most recently updated non-archived idea
        index = load_index()
        active = [e for e in index if e.status != IdeaStatus.ARCHIVED.value]
        if not active:
            console.print("[dim]No active ideas found.[/dim]")
            return
        most_recent = max(active, key=lambda e: e.updated)
        idea_id = most_recent.id

    path = find_idea_by_id(idea_id)
    if path is None:
        console.print(f"[red]Error:[/red] Idea not found: {idea_id}")
        sys.exit(1)

    try:
        fm, _ = load_idea(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Print resume summary
    console.print("[bold]Resume Context[/bold]\n")
    console.print(f"[bold]{fm.title}[/bold]")
    status_line = (
        f"{STATUS_EMOJI[fm.status]} {fm.status.value} | "
        f"{fm.type.value} | {_format_tags_display(fm.tags)}"
    )
    console.print(status_line)
    console.print(f"\n[dim]ID: {fm.id}[/dim]")
    console.print(f"[dim]File: {path}[/dim]")
    console.print(f"[dim]Created: {fm.created}[/dim]")
    console.print(f"[dim]Updated: {fm.updated}[/dim]")

    if fm.workflow:
        phase = fm.workflow.get("phase", "N/A")
        iteration = fm.workflow.get("iteration", 0)
        console.print(
            f"\n[bold]Workflow State:[/bold] Phase: {phase}, Iteration: {iteration}"
        )

    if fm.related_ideas:
        console.print("\n[bold]Related Ideas:[/bold]")
        for rel_id in fm.related_ideas:
            rel_path = find_idea_by_id(rel_id)
            if rel_path:
                try:
                    rel_fm, _ = load_idea(rel_path)
                    emoji = STATUS_EMOJI[rel_fm.status]
                    console.print(f"  {emoji} {rel_fm.title}")
                    console.print(f"      [dim]ID: {rel_id}[/dim]")
                except (ValueError, FileNotFoundError):
                    console.print(f"  [dim]{rel_id}[/dim]")
            else:
                console.print(f"  [dim]{rel_id} (not found)[/dim]")

    if fm.references:
        console.print("\n[bold]References:[/bold]")
        for ref in fm.references:
            title = ref.get("title", "Untitled")
            url = ref.get("url", "")
            console.print(f"  - {title}: {url}")

    console.print("\n---")
    console.print(f"\nTo view full content: [bold]oaps idea show {fm.id}[/bold]")


def _update_idea_header(body: str, fm: IdeaFrontmatter) -> str:
    """Update the idea header section in body.

    Args:
        body: Current body content.
        fm: Updated frontmatter.

    Returns:
        Body with updated header.
    """
    import re

    tags_display = _format_tags_display(fm.tags)
    emoji = STATUS_EMOJI[fm.status]
    status_val = fm.status.value
    type_val = fm.type.value
    header_line = f"{emoji} **{status_val}** | {type_val} | {tags_display}"
    new_header = f"<!-- idea-header-start -->\n{header_line}\n<!-- idea-header-end -->"

    # Replace existing header or prepend
    pattern = r"<!-- idea-header-start -->.*?<!-- idea-header-end -->"
    if re.search(pattern, body, re.DOTALL):
        return re.sub(pattern, new_header, body, flags=re.DOTALL)
    return new_header + "\n\n" + body


def _update_idea_footer(body: str, fm: IdeaFrontmatter) -> str:
    """Update the idea footer section in body.

    Args:
        body: Current body content.
        fm: Updated frontmatter.

    Returns:
        Body with updated footer.
    """
    import re

    refs_display = "None yet"
    if fm.references:
        refs_display = ", ".join(
            r.get("title", r.get("url", "")) for r in fm.references
        )

    related_display = "None yet"
    if fm.related_ideas:
        related_display = ", ".join(fm.related_ideas)

    new_footer = (
        f"<!-- idea-footer-start -->\n"
        f"---\n"
        f"**References**: {refs_display}\n"
        f"**Related Ideas**: {related_display}\n"
        f"<!-- idea-footer-end -->"
    )

    # Replace existing footer or append
    pattern = r"<!-- idea-footer-start -->.*?<!-- idea-footer-end -->"
    if re.search(pattern, body, re.DOTALL):
        return re.sub(pattern, new_footer, body, flags=re.DOTALL)
    return body.rstrip() + "\n\n" + new_footer


def _update_index_entry(fm: IdeaFrontmatter) -> None:
    """Update an idea's entry in the index.

    Args:
        fm: The updated frontmatter.
    """
    index = load_index()

    # Find and update the entry
    new_index: list[IdeaIndexEntry] = []
    for entry in index:
        if entry.id == fm.id:
            new_entry = IdeaIndexEntry(
                id=fm.id,
                title=fm.title,
                status=fm.status.value,
                type=fm.type.value,
                tags=fm.tags,
                file_path=entry.file_path,
                created=fm.created,
                updated=fm.updated,
                author=fm.author,
            )
            new_index.append(new_entry)
        else:
            new_index.append(entry)

    save_index(new_index)
