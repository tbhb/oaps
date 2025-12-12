# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAny=false
"""Idea workflow orchestration actions for hooks.

This module provides Python action entrypoints for hook rules that manage
the idea workflow state and file updates.

All functions follow the hook action signature:
    def action_name(context: HookContext) -> dict[str, object] | None

Return values can include:
- "deny_message": str - Block the operation
- "warn_message": str - Warning message to display
- "suggest_message": str - Suggestion message to display
"""

import json
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from oaps.hooks._context import HookContext
    from oaps.session import Session


# Constants
_ACTIVE = 1
_INACTIVE = 0


# -----------------------------------------------------------------------------
# Workflow initialization
# -----------------------------------------------------------------------------


def init_idea_workflow(context: HookContext) -> dict[str, object]:
    """Initialize /idea workflow state.

    Called on user_prompt_submit when /idea command is detected.
    Creates workflow ID and initializes phase tracking.

    Args:
        context: Hook context with session access.

    Returns:
        Status dict with workflow_id.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session available"}

    workflow_id = str(uuid.uuid4())[:8]

    session.set("idea.workflow_id", workflow_id)
    session.set("idea.active", _ACTIVE)
    session.set("idea.phase", "seed")
    _ = session.set_timestamp("idea.started_at")

    # Extract title from prompt
    prompt = _get_prompt(context)
    title = _extract_idea_title(prompt)
    if title:
        session.set("idea.title", title)

    session.set("idea.document_created", _INACTIVE)
    session.set("idea.status", "seed")

    msg = f"Idea workflow {workflow_id} initialized. Let's capture your idea."
    return {
        "status": "initialized",
        "workflow_id": workflow_id,
        "suggest_message": msg,
    }


# -----------------------------------------------------------------------------
# Document tracking
# -----------------------------------------------------------------------------


def track_document_creation(context: HookContext) -> dict[str, object]:
    """Track idea document creation.

    Called after Write to .oaps/docs/ideas/*.md when document_created is false.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict with path.
    """
    session = _get_session(context)
    if session is None:
        return {"error": "No session"}

    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"error": "No tool input"}

    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return {"error": "Invalid file path"}

    session.set("idea.document_created", _ACTIVE)
    session.set("idea.idea_path", file_path)
    session.set("idea.phase", "exploring")

    # Extract idea ID from filename
    filename = Path(file_path).stem
    session.set("idea.idea_id", filename)

    return {"status": "document_created", "path": file_path}


# -----------------------------------------------------------------------------
# Document formatting
# -----------------------------------------------------------------------------


def update_idea_header_footer(context: HookContext) -> dict[str, object]:
    """Update idea document header/footer from frontmatter.

    Parses frontmatter and regenerates the header/footer sections
    between the HTML comment delimiters.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict indicating update result.
    """
    import pendulum  # noqa: PLC0415

    from oaps.templating import load_frontmatter_file  # noqa: PLC0415

    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"error": "No tool input"}

    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return {"error": "Invalid file path"}

    path = Path(file_path)
    if not path.exists():
        return {"warn_message": f"File not found: {file_path}"}

    try:
        frontmatter, body = load_frontmatter_file(path)
        if frontmatter is None:
            return {"warn_message": "No frontmatter found"}

        # Generate new header
        status = frontmatter.get("status", "seed")
        idea_type = frontmatter.get("type", "technical")
        tags = frontmatter.get("tags", [])

        status_emoji = {
            "seed": "S",
            "exploring": "E",
            "refining": "R",
            "crystallized": "C",
            "archived": "A",
        }.get(str(status), "?")

        tags_display = ""
        if isinstance(tags, list):
            tags_display = " ".join(f"`{t}`" for t in tags)

        status_title = str(status).title()
        type_title = str(idea_type).title()
        header = f"{status_emoji} **{status_title}** | {type_title} | {tags_display}"

        # Generate new footer
        references = frontmatter.get("references", [])
        related = frontmatter.get("related_ideas", [])

        refs_display = "None yet"
        if isinstance(references, list) and references:
            refs_parts = []
            for r in references:
                if isinstance(r, dict):
                    title = r.get("title", "Link")
                    url = r.get("url", "")
                    refs_parts.append(f"[{title}]({url})")
            if refs_parts:
                refs_display = ", ".join(refs_parts)

        related_display = "None yet"
        if isinstance(related, list) and related:
            related_display = ", ".join(f"[{r}](./{r}.md)" for r in related)

        footer = f"**References**: {refs_display}\n**Related Ideas**: {related_display}"

        # Replace header/footer in body
        new_body = _replace_section(
            body, "idea-header-start", "idea-header-end", header
        )
        new_body = _replace_section(
            new_body, "idea-footer-start", "idea-footer-end", footer
        )

        if new_body != body:
            # Update timestamp in frontmatter
            frontmatter["updated"] = pendulum.now("UTC").to_iso8601_string()

            # Write the file with updated frontmatter and body
            _write_frontmatter_file(path, dict(frontmatter), new_body)

    except (OSError, ValueError) as e:
        context.hook_logger.warning("Failed to update header/footer", error=str(e))
        return {"warn_message": f"Could not update header/footer: {e}"}

    return {"status": "header_footer_updated"}


# -----------------------------------------------------------------------------
# Index management
# -----------------------------------------------------------------------------


def update_idea_index(context: HookContext) -> dict[str, object]:
    """Update ideas index after document change.

    Reads the modified idea document and updates its entry in index.json.

    Args:
        context: Hook context with tool output.

    Returns:
        Status dict indicating update result.
    """
    import pendulum  # noqa: PLC0415

    from oaps.templating import load_frontmatter_file  # noqa: PLC0415
    from oaps.utils._paths import get_oaps_dir  # noqa: PLC0415

    tool_input = _get_tool_input(context)
    if not tool_input:
        return {"error": "No tool input"}

    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return {"error": "Invalid file path"}

    path = Path(file_path)
    if not path.exists():
        return {"warn_message": f"File not found: {file_path}"}

    idea_id: object = path.stem

    try:
        frontmatter, _ = load_frontmatter_file(path)
        if frontmatter is None:
            return {"warn_message": "No frontmatter found"}

        # Load existing index
        ideas_dir = get_oaps_dir() / "docs" / "ideas"
        index_path = ideas_dir / "index.json"

        index_data: dict[str, object] = {"updated": "", "ideas": []}
        if index_path.exists():
            with index_path.open() as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    index_data = loaded

        # Find or create entry
        idea_id = frontmatter.get("id", path.stem)
        entries_raw = index_data.get("ideas", [])
        entries: list[dict[str, object]] = []
        if isinstance(entries_raw, list):
            entries = [e for e in entries_raw if isinstance(e, dict)]

        # Remove existing entry if present
        entries = [e for e in entries if e.get("id") != idea_id]

        # Add updated entry
        entries.append(
            {
                "id": idea_id,
                "title": frontmatter.get("title", ""),
                "status": frontmatter.get("status", "seed"),
                "type": frontmatter.get("type", "technical"),
                "tags": frontmatter.get("tags", []),
                "file_path": path.name,
                "created": frontmatter.get("created", ""),
                "updated": frontmatter.get("updated", ""),
                "author": frontmatter.get("author"),
            }
        )

        # Sort by updated timestamp descending
        entries.sort(key=lambda e: str(e.get("updated", "")), reverse=True)

        # Save index
        index_data["updated"] = pendulum.now("UTC").to_iso8601_string()
        index_data["ideas"] = entries

        ideas_dir.mkdir(parents=True, exist_ok=True)
        with index_path.open("w") as f:
            json.dump(index_data, f, indent=2)

    except (OSError, ValueError, json.JSONDecodeError) as e:
        context.hook_logger.warning("Failed to update index", error=str(e))
        return {"warn_message": f"Could not update index: {e}"}

    return {"status": "index_updated", "idea_id": idea_id}


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _get_session(context: HookContext) -> Session | None:
    """Get Session from context."""
    from oaps.session import Session  # noqa: PLC0415
    from oaps.utils import create_state_store  # noqa: PLC0415

    if not hasattr(context, "oaps_state_file"):
        return None

    try:
        store = create_state_store(
            context.oaps_state_file, session_id=context.claude_session_id
        )
        return Session(id=context.claude_session_id, store=store)
    except Exception:  # noqa: BLE001
        return None


def _get_prompt(context: HookContext) -> str:
    """Extract prompt from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "prompt"):
        prompt = getattr(hook_input, "prompt", "")
        return str(prompt) if prompt else ""
    return ""


def _get_tool_input(context: HookContext) -> dict[str, object] | None:
    """Extract tool input from hook input."""
    hook_input = context.hook_input
    if hasattr(hook_input, "tool_input"):
        tool_input = getattr(hook_input, "tool_input", None)
        if isinstance(tool_input, dict):
            return dict(tool_input)
    return None


def _extract_idea_title(prompt: str) -> str:
    """Extract idea title from command prompt."""
    if not prompt:
        return ""

    text = prompt
    for prefix in ["/idea", "/oaps:idea"]:
        if text.lower().startswith(prefix):
            text = text[len(prefix) :].strip()
            break

    # Remove flags
    text = re.sub(r"--\w+\s*\S*", "", text).strip()

    # Return first line or first 100 chars
    first_line = text.split("\n")[0].strip()
    return first_line[:100] if first_line else ""


def _replace_section(
    body: str, start_marker: str, end_marker: str, content: str
) -> str:
    """Replace content between HTML comment markers."""
    pattern = rf"(<!--\s*{start_marker}\s*-->).*?(<!--\s*{end_marker}\s*-->)"
    replacement = rf"\1\n{content}\n\2"
    return re.sub(pattern, replacement, body, flags=re.DOTALL)


def _write_frontmatter_file(
    path: Path, frontmatter: dict[str, object], body: str
) -> None:
    """Write a markdown file with YAML frontmatter.

    Args:
        path: Path to the markdown file.
        frontmatter: Dictionary of frontmatter data.
        body: The markdown body content.
    """
    import yaml  # noqa: PLC0415

    frontmatter_str = yaml.safe_dump(
        frontmatter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )
    content = f"---\n{frontmatter_str}---\n{body}"
    _ = path.write_text(content, encoding="utf-8")
