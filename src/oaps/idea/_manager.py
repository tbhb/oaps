# pyright: reportAny=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
# pyright: reportExplicitAny=false, reportUnknownMemberType=false
"""Idea manager for CRUD operations on ideas.

This module provides the IdeaManager class for managing ideas in
`.oaps/docs/ideas/`. It maintains an index for fast listing and supports
full-text search across idea content.
"""

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

import pendulum

from oaps.cli._commands._idea._models import IdeaFrontmatter, IdeaIndexEntry
from oaps.cli._commands._idea._storage import (
    generate_idea_id,
    idea_filename,
    load_idea as storage_load_idea,
    load_index as storage_load_index,
    rebuild_index as storage_rebuild_index,
    save_idea as storage_save_idea,
    save_index as storage_save_index,
)
from oaps.exceptions import IdeaNotFoundError, IdeaValidationError
from oaps.idea._models import Idea, IdeaReference, IdeaStatus, IdeaSummary, IdeaType
from oaps.spec._io import append_jsonl
from oaps.utils._paths import get_oaps_dir

if TYPE_CHECKING:
    from pathlib import Path

    from oaps.repository import OapsRepository

__all__ = ["IdeaManager"]

# Index schema version
_INDEX_VERSION: Final = 1


class IdeaManager:
    """Manager for CRUD operations on ideas.

    The IdeaManager provides methods for creating, reading, updating, and
    searching ideas in `.oaps/docs/ideas/`. It maintains an index for fast
    listing operations.

    Attributes:
        _ideas_dir: Directory containing idea files.
        _oaps_repo: Optional repository for committing changes.
        _index_cache: Cached index data.
    """

    __slots__: Final = ("_ideas_dir", "_index_cache", "_oaps_repo")

    _ideas_dir: Path
    _oaps_repo: OapsRepository | None
    _index_cache: list[IdeaIndexEntry] | None

    def __init__(
        self,
        ideas_dir: Path | None = None,
        oaps_repo: OapsRepository | None = None,
    ) -> None:
        """Initialize the idea manager.

        Args:
            ideas_dir: Directory for idea files. If None, uses the default
                `.oaps/docs/ideas/` location.
            oaps_repo: Repository for committing changes. If None, mutations
                work but changes are not committed. For testing, pass None
                to skip commits entirely.
        """
        if ideas_dir is None:
            ideas_dir = get_oaps_dir() / "docs" / "ideas"
        self._ideas_dir = ideas_dir
        self._oaps_repo = oaps_repo
        self._index_cache = None

    # -------------------------------------------------------------------------
    # Path Properties
    # -------------------------------------------------------------------------

    @property
    def ideas_dir(self) -> Path:
        """Path to the ideas directory."""
        return self._ideas_dir

    @property
    def index_path(self) -> Path:
        """Path to the index.json file."""
        return self._ideas_dir / "index.json"

    @property
    def history_path(self) -> Path:
        """Path to the history.jsonl file."""
        return self._ideas_dir / "history.jsonl"

    # -------------------------------------------------------------------------
    # Internal Methods - Caching
    # -------------------------------------------------------------------------

    def _invalidate_caches(self, idea_id: str | None = None) -> None:
        """Invalidate cached data.

        Args:
            idea_id: If provided, only for documentation. Currently all
                invalidation clears the full cache as we only cache the index.
        """
        _ = idea_id  # Unused but kept for API consistency with SpecManager
        self._index_cache = None

    # -------------------------------------------------------------------------
    # Internal Methods - Index I/O
    # -------------------------------------------------------------------------

    def _load_index(self) -> list[IdeaIndexEntry]:
        """Load the index from disk.

        Returns:
            The index data as a list of IdeaIndexEntry.
        """
        if self._index_cache is not None:
            return self._index_cache

        self._index_cache = storage_load_index()
        return self._index_cache

    def _write_index(self, entries: list[IdeaIndexEntry]) -> None:
        """Write the index to disk.

        Args:
            entries: List of IdeaIndexEntry to save.
        """
        storage_save_index(entries)
        self._index_cache = None

    def _update_index_entry(self, idea: Idea) -> None:
        """Update or add an idea's entry in the index.

        Args:
            idea: The idea to update in the index.
        """
        entries = list(self._load_index())
        new_entry = self._idea_to_index_entry(idea)

        # Find and replace existing entry, or append if not found
        found = False
        for i, entry in enumerate(entries):
            if entry.id == idea.id:
                entries[i] = new_entry
                found = True
                break

        if not found:
            entries.append(new_entry)

        self._write_index(entries)

    # -------------------------------------------------------------------------
    # Internal Methods - Idea I/O
    # -------------------------------------------------------------------------

    def _idea_path(self, idea_id: str) -> Path:
        """Get the file path for an idea.

        Args:
            idea_id: The idea ID.

        Returns:
            Path to the idea markdown file.
        """
        return self._ideas_dir / idea_filename(idea_id)

    def _load_idea(self, idea_id: str) -> Idea:
        """Load a full idea from disk.

        Args:
            idea_id: The idea ID to load.

        Returns:
            The loaded Idea instance.

        Raises:
            IdeaNotFoundError: If the idea file doesn't exist.
        """
        path = self._idea_path(idea_id)
        if not path.exists():
            msg = f"Idea not found: {idea_id}"
            raise IdeaNotFoundError(msg, idea_id=idea_id)

        try:
            fm, body = storage_load_idea(path)
        except (FileNotFoundError, ValueError) as e:
            msg = f"Failed to load idea: {idea_id}"
            raise IdeaNotFoundError(msg, idea_id=idea_id) from e

        return self._frontmatter_to_idea(fm, body, path.name)

    def _frontmatter_to_idea(
        self, fm: IdeaFrontmatter, body: str, file_path: str
    ) -> Idea:
        """Convert IdeaFrontmatter to Idea dataclass.

        Args:
            fm: The frontmatter data.
            body: The markdown body content.
            file_path: The relative file path.

        Returns:
            The Idea instance with parsed datetime fields.
        """
        created = self._parse_datetime(fm.created)
        updated = self._parse_datetime(fm.updated)

        return Idea(
            id=fm.id,
            title=fm.title,
            status=fm.status,
            idea_type=fm.type,
            created=created,
            updated=updated,
            body=body,
            tags=fm.tags,
            author=fm.author,
            related_ideas=fm.related_ideas,
            references=fm.references,
            workflow=fm.workflow,
            file_path=file_path,
        )

    def _idea_to_frontmatter(self, idea: Idea) -> IdeaFrontmatter:
        """Convert Idea dataclass to IdeaFrontmatter.

        Args:
            idea: The idea to convert.

        Returns:
            IdeaFrontmatter with string datetime fields.
        """
        return IdeaFrontmatter(
            id=idea.id,
            title=idea.title,
            status=idea.status,
            type=idea.idea_type,
            created=idea.created.isoformat(),
            updated=idea.updated.isoformat(),
            author=idea.author,
            tags=idea.tags,
            related_ideas=idea.related_ideas,
            references=idea.references,
            workflow=idea.workflow,
        )

    def _save_idea(self, idea: Idea) -> Path:
        """Save an idea to disk.

        Args:
            idea: The idea to save.

        Returns:
            Path to the saved file.
        """
        path = self._idea_path(idea.id)
        self._ideas_dir.mkdir(parents=True, exist_ok=True)

        fm = self._idea_to_frontmatter(idea)
        storage_save_idea(path, fm, idea.body)
        return path

    def _parse_datetime(self, value: str) -> datetime:
        """Parse a datetime string to datetime object.

        Args:
            value: ISO format datetime string.

        Returns:
            Parsed datetime object.
        """
        # Use standard library for ISO format parsing
        # This handles the common case of ISO 8601 strings from our own serialization
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            # Fallback to pendulum for more flexible parsing (non-standard formats)
            parsed = pendulum.parse(value)
            # pendulum.parse can return DateTime, Date, Time, or Duration
            # For date/datetime types, convert via isoformat round-trip
            iso_str: str = parsed.isoformat()  # pyright: ignore[reportAttributeAccessIssue]
            return datetime.fromisoformat(iso_str)

    # -------------------------------------------------------------------------
    # Internal Methods - History
    # -------------------------------------------------------------------------

    def _record_history(
        self,
        event: str,
        actor: str,
        idea_id: str,
        from_value: str | None = None,
        to_value: str | None = None,
    ) -> None:
        """Record an event to the history log.

        Args:
            event: The event type (e.g., "created", "updated", "archived").
            actor: The actor who performed the action.
            idea_id: The affected idea ID.
            from_value: The previous value (for updates).
            to_value: The new value (for updates).
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "actor": actor,
            "id": idea_id,
        }
        if from_value is not None:
            entry["from_value"] = from_value
        if to_value is not None:
            entry["to_value"] = to_value

        self._ideas_dir.mkdir(parents=True, exist_ok=True)
        append_jsonl(self.history_path, entry)

    # -------------------------------------------------------------------------
    # Internal Methods - Repository Integration
    # -------------------------------------------------------------------------

    def _commit(
        self, workflow: str, action: str, *, session_id: str | None = None
    ) -> bool:
        """Commit changes to the OAPS repository.

        Args:
            workflow: The workflow name (always "idea").
            action: The action description for the commit message.
            session_id: Optional session identifier for the commit trailer.

        Returns:
            True if commit was made, False if no repository or no changes.
        """
        if self._oaps_repo is None:
            return False

        result = self._oaps_repo.checkpoint(
            workflow=workflow,
            action=action,
            session_id=session_id,
        )
        return not result.no_changes

    # -------------------------------------------------------------------------
    # Internal Methods - Index Conversion
    # -------------------------------------------------------------------------

    def _idea_to_index_entry(self, idea: Idea) -> IdeaIndexEntry:
        """Convert an Idea to an IdeaIndexEntry.

        Args:
            idea: The idea to convert.

        Returns:
            IdeaIndexEntry suitable for index storage.
        """
        return IdeaIndexEntry(
            id=idea.id,
            title=idea.title,
            status=idea.status.value,
            type=idea.idea_type.value,
            tags=idea.tags,
            file_path=idea.file_path or idea_filename(idea.id),
            created=idea.created.isoformat(),
            updated=idea.updated.isoformat(),
            author=idea.author,
        )

    def _index_entry_to_summary(self, entry: IdeaIndexEntry) -> IdeaSummary:
        """Convert an IdeaIndexEntry to an IdeaSummary.

        Args:
            entry: IdeaIndexEntry from index storage.

        Returns:
            IdeaSummary instance.
        """
        return IdeaSummary(
            id=entry.id,
            title=entry.title,
            status=IdeaStatus(entry.status),
            idea_type=IdeaType(entry.type),
            created=self._parse_datetime(entry.created),
            updated=self._parse_datetime(entry.updated),
            tags=entry.tags,
            author=entry.author,
            file_path=entry.file_path,
        )

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def exists(self, idea_id: str) -> bool:
        """Check if an idea exists.

        Args:
            idea_id: The idea ID to check.

        Returns:
            True if the idea exists in the index.
        """
        entries = self._load_index()
        return any(entry.id == idea_id for entry in entries)

    def get(self, idea_id: str) -> Idea:
        """Get a full idea by ID.

        Args:
            idea_id: The idea ID.

        Returns:
            The full Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
        """
        return self._load_idea(idea_id)

    def list(
        self,
        *,
        status: IdeaStatus | None = None,
        idea_type: IdeaType | None = None,
        tags: list[str] | None = None,
        include_archived: bool = False,
    ) -> list[IdeaSummary]:
        """List ideas with optional filtering.

        Args:
            status: Filter by status.
            idea_type: Filter by type.
            tags: Filter by tags (ideas must have all listed tags).
            include_archived: Include archived ideas in results.

        Returns:
            List of matching idea summaries.
        """
        entries = self._load_index()

        results: list[IdeaSummary] = []
        for entry in entries:
            summary = self._index_entry_to_summary(entry)

            # Apply status filter
            if status is not None and summary.status != status:
                continue

            # Apply type filter
            if idea_type is not None and summary.idea_type != idea_type:
                continue

            # Apply tags filter
            if tags and not all(tag in summary.tags for tag in tags):
                continue

            # Apply archived filter
            if not include_archived and summary.status == IdeaStatus.ARCHIVED:
                continue

            results.append(summary)

        return results

    def search(
        self,
        query: str,
        *,
        fields: list[str] | None = None,
    ) -> list[IdeaSummary]:
        """Search ideas by text query.

        Performs case-insensitive substring search across specified fields.
        By default, searches title, body, and tags.

        Args:
            query: The search query string.
            fields: Fields to search. Defaults to ["title", "body", "tags"].
                Valid fields: "title", "body", "tags", "id", "author".

        Returns:
            List of matching idea summaries.
        """
        if fields is None:
            fields = ["title", "body", "tags"]

        query_lower = query.lower()
        results: list[IdeaSummary] = []

        entries = self._load_index()

        for entry in entries:
            matched = False

            # Check index fields first (avoid loading full idea if possible)
            if "title" in fields and query_lower in entry.title.lower():
                matched = True

            if (
                not matched
                and "tags" in fields
                and any(query_lower in tag.lower() for tag in entry.tags)
            ):
                matched = True

            if not matched and "id" in fields and query_lower in entry.id.lower():
                matched = True

            if not matched and "author" in fields:
                author = entry.author or ""
                if query_lower in author.lower():
                    matched = True

            # If body search needed and not already matched, load full idea
            if not matched and "body" in fields:
                try:
                    full_idea = self._load_idea(entry.id)
                    if query_lower in full_idea.body.lower():
                        matched = True
                except IdeaNotFoundError:
                    continue

            if matched:
                results.append(self._index_entry_to_summary(entry))

        return results

    # -------------------------------------------------------------------------
    # Mutation Methods
    # -------------------------------------------------------------------------

    def create(
        self,
        title: str,
        idea_type: IdeaType,
        *,
        tags: list[str] | None = None,
        body: str = "",
        author: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Create a new idea.

        Args:
            title: The idea title.
            idea_type: The type of idea.
            tags: Optional tags for the idea.
            body: The markdown body content.
            author: The idea author.
            session_id: Optional session ID for commit trailer.

        Returns:
            The created Idea instance.

        Raises:
            IdeaValidationError: If validation fails.
        """
        # Validate title
        if not title.strip():
            msg = "Idea title cannot be empty"
            raise IdeaValidationError(msg, field="title", expected="non-empty string")

        # Generate ID
        idea_id = generate_idea_id(title)

        # Create timestamps
        now = datetime.now(UTC)

        # Create the idea
        idea = Idea(
            id=idea_id,
            title=title,
            status=IdeaStatus.SEED,
            idea_type=idea_type,
            created=now,
            updated=now,
            body=body,
            tags=tuple(tags) if tags else (),
            author=author,
            file_path=idea_filename(idea_id),
        )

        # Save the idea file
        _ = self._save_idea(idea)

        # Update index
        self._update_index_entry(idea)

        # Record history
        self._record_history("created", author or "unknown", idea_id)

        # Commit changes
        _ = self._commit("idea", f"create {idea_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return idea

    def update_status(
        self,
        idea_id: str,
        status: IdeaStatus,
        *,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Update an idea's status.

        Args:
            idea_id: The idea ID to update.
            status: The new status.
            actor: The actor performing the update.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
        """
        idea = self._load_idea(idea_id)
        old_status = idea.status

        # Update the idea
        now = datetime.now(UTC)
        updated_idea = replace(idea, status=status, updated=now)

        # Save the idea file
        _ = self._save_idea(updated_idea)

        # Update index
        self._update_index_entry(updated_idea)

        # Record history
        self._record_history(
            "status_updated",
            actor or "unknown",
            idea_id,
            from_value=old_status.value,
            to_value=status.value,
        )

        # Commit changes
        _ = self._commit(
            "idea", f"update {idea_id} status to {status.value}", session_id=session_id
        )

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return updated_idea

    def update_content(
        self,
        idea_id: str,
        body: str,
        *,
        title: str | None = None,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Update an idea's content.

        Args:
            idea_id: The idea ID to update.
            body: The new body content.
            title: Optional new title.
            actor: The actor performing the update.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
            IdeaValidationError: If new title is empty.
        """
        idea = self._load_idea(idea_id)

        # Validate title if provided
        new_title = title if title is not None else idea.title
        if not new_title.strip():
            msg = "Idea title cannot be empty"
            raise IdeaValidationError(
                msg, idea_id=idea_id, field="title", expected="non-empty string"
            )

        # Update the idea
        now = datetime.now(UTC)
        updated_idea = replace(idea, body=body, title=new_title, updated=now)

        # Save the idea file
        _ = self._save_idea(updated_idea)

        # Update index if title changed
        if title is not None:
            self._update_index_entry(updated_idea)

        # Record history
        self._record_history("content_updated", actor or "unknown", idea_id)

        # Commit changes
        _ = self._commit("idea", f"update {idea_id} content", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return updated_idea

    def add_reference(
        self,
        idea_id: str,
        url: str,
        title: str,
        *,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Add a reference to an idea.

        Args:
            idea_id: The idea ID to update.
            url: The reference URL.
            title: The reference title.
            actor: The actor performing the update.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
            IdeaValidationError: If URL or title is empty.
        """
        if not url.strip():
            msg = "Reference URL cannot be empty"
            raise IdeaValidationError(
                msg, idea_id=idea_id, field="url", expected="non-empty string"
            )
        if not title.strip():
            msg = "Reference title cannot be empty"
            raise IdeaValidationError(
                msg, idea_id=idea_id, field="title", expected="non-empty string"
            )

        idea = self._load_idea(idea_id)

        # Create new reference
        new_ref = IdeaReference(url=url, title=title)

        # Update the idea
        now = datetime.now(UTC)
        updated_idea = replace(
            idea,
            references=(*idea.references, new_ref),
            updated=now,
        )

        # Save the idea file
        _ = self._save_idea(updated_idea)

        # Record history
        self._record_history(
            "reference_added", actor or "unknown", idea_id, to_value=url
        )

        # Commit changes
        _ = self._commit("idea", f"add reference to {idea_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return updated_idea

    def add_tags(
        self,
        idea_id: str,
        tags: list[str],
        *,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Add tags to an idea.

        Args:
            idea_id: The idea ID to update.
            tags: Tags to add.
            actor: The actor performing the update.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
        """
        idea = self._load_idea(idea_id)

        # Merge tags (avoiding duplicates)
        existing_tags = set(idea.tags)
        new_tags = tuple(sorted(existing_tags | set(tags)))

        # Update the idea
        now = datetime.now(UTC)
        updated_idea = replace(idea, tags=new_tags, updated=now)

        # Save the idea file
        _ = self._save_idea(updated_idea)

        # Update index
        self._update_index_entry(updated_idea)

        # Record history
        self._record_history(
            "tags_added", actor or "unknown", idea_id, to_value=", ".join(tags)
        )

        # Commit changes
        _ = self._commit("idea", f"add tags to {idea_id}", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return updated_idea

    def link_ideas(
        self,
        idea_id: str,
        related_ids: list[str],
        *,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Link an idea to related ideas.

        Args:
            idea_id: The idea ID to update.
            related_ids: IDs of related ideas to link.
            actor: The actor performing the update.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea or any related idea doesn't exist.
        """
        idea = self._load_idea(idea_id)

        # Validate related ideas exist
        for related_id in related_ids:
            if not self.exists(related_id):
                msg = f"Related idea not found: {related_id}"
                raise IdeaNotFoundError(msg, idea_id=related_id)

        # Merge related ideas (avoiding duplicates and self-references)
        existing_related = set(idea.related_ideas)
        new_related = existing_related | set(related_ids)
        new_related.discard(idea_id)  # Prevent self-reference
        new_related_tuple = tuple(sorted(new_related))

        # Update the idea
        now = datetime.now(UTC)
        updated_idea = replace(idea, related_ideas=new_related_tuple, updated=now)

        # Save the idea file
        _ = self._save_idea(updated_idea)

        # Record history
        self._record_history(
            "ideas_linked",
            actor or "unknown",
            idea_id,
            to_value=", ".join(related_ids),
        )

        # Commit changes
        _ = self._commit("idea", f"link {idea_id} to related", session_id=session_id)

        # Invalidate caches
        self._invalidate_caches(idea_id)

        return updated_idea

    def archive(
        self,
        idea_id: str,
        *,
        actor: str | None = None,
        session_id: str | None = None,
    ) -> Idea:
        """Archive an idea.

        This is a convenience method that delegates to update_status with
        IdeaStatus.ARCHIVED.

        Args:
            idea_id: The idea ID to archive.
            actor: The actor performing the archive.
            session_id: Optional session ID for commit trailer.

        Returns:
            The updated Idea instance.

        Raises:
            IdeaNotFoundError: If the idea doesn't exist.
        """
        return self.update_status(
            idea_id,
            IdeaStatus.ARCHIVED,
            actor=actor,
            session_id=session_id,
        )

    # -------------------------------------------------------------------------
    # Index Maintenance
    # -------------------------------------------------------------------------

    def rebuild_index(self) -> int:
        """Rebuild the index from filesystem.

        Scans all .md files in the ideas directory and rebuilds the index.
        Useful for recovering from index corruption or syncing after manual edits.

        Returns:
            Number of ideas found and indexed.
        """
        if not self._ideas_dir.exists():
            self._write_index([])
            return 0

        entries = storage_rebuild_index()
        self._invalidate_caches()
        return len(entries)
