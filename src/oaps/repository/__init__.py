"""OAPS repository management.

This package provides classes for managing Git repositories with scoped
access control and type-safe dependency injection.

Classes:
    OapsRepository: Scoped operations for .oaps/ directory.
    ProjectRepository: Scoped operations for project repository (excludes .oaps/).
    BaseRepository: Abstract base class with shared git functionality.
    RepositoryProtocol: Runtime-checkable protocol for dependency injection.

Models:
    OapsRepoStatus: Status snapshot for OAPS repository.
    ProjectRepoStatus: Status snapshot for project repository.
    RepoStatus: Type alias for OapsRepoStatus | ProjectRepoStatus.
    CommitResult: Result of commit operations.
    CommitInfo: Metadata about a single commit.
    DiscardResult: Result of discard_changes operations.
    FileDiffStats: Diff statistics for a single file.
    DiffStats: Aggregate diff statistics.
    BlameLine: Information about a single blamed line.

Example:
    >>> from oaps.repository import OapsRepository, ProjectRepository
    >>> with OapsRepository() as oaps_repo:
    ...     if oaps_repo.has_changes():
    ...         oaps_repo.commit_pending("Auto-save config")
    >>> with ProjectRepository() as project_repo:
    ...     status = project_repo.get_status()
"""

from oaps.repository._base import BaseRepository
from oaps.repository._fake import FakeRepository
from oaps.repository._models import (
    BlameLine,
    CommitInfo,
    CommitResult,
    DiffStats,
    DiscardResult,
    FileDiffStats,
    OapsRepoStatus,
    ProjectRepoStatus,
    RepoStatus,
)
from oaps.repository._project import ProjectRepository
from oaps.repository._protocol import RepositoryProtocol
from oaps.repository._repository import OapsRepository

__all__ = [
    "BaseRepository",
    "BlameLine",
    "CommitInfo",
    "CommitResult",
    "DiffStats",
    "DiscardResult",
    "FakeRepository",
    "FileDiffStats",
    "OapsRepoStatus",
    "OapsRepository",
    "ProjectRepoStatus",
    "ProjectRepository",
    "RepoStatus",
    "RepositoryProtocol",
]
