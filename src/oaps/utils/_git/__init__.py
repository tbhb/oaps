"""Git utilities for OAPS.

This package provides git-related utilities including repository context
collection, worktree management, and common helper functions.
"""

from oaps.utils._git._common import (
    decode_bytes,
    discover_repo,
    get_main_repo,
    get_main_worktree_dir,
    get_worktree_dir,
    resolve_repo,
    strip_refs_heads,
)
from oaps.utils._git._context import GitContext
from oaps.utils._git._status import get_git_context
from oaps.utils._git._worktree import (
    WorktreeAddResult,
    WorktreeInfo,
    WorktreePruneResult,
    add_worktree,
    get_main_worktree,
    get_oaps_repository_for_worktree,
    get_project_repository_for_worktree,
    get_worktree,
    get_worktree_for_path,
    is_in_worktree,
    is_main_worktree,
    list_worktrees,
    lock_worktree,
    move_worktree,
    prune_worktrees,
    remove_worktree,
    unlock_worktree,
)

__all__ = [
    "GitContext",
    "WorktreeAddResult",
    "WorktreeInfo",
    "WorktreePruneResult",
    "add_worktree",
    "decode_bytes",
    "discover_repo",
    "get_git_context",
    "get_main_repo",
    "get_main_worktree",
    "get_main_worktree_dir",
    "get_oaps_repository_for_worktree",
    "get_project_repository_for_worktree",
    "get_worktree",
    "get_worktree_dir",
    "get_worktree_for_path",
    "is_in_worktree",
    "is_main_worktree",
    "list_worktrees",
    "lock_worktree",
    "move_worktree",
    "prune_worktrees",
    "remove_worktree",
    "resolve_repo",
    "strip_refs_heads",
    "unlock_worktree",
]
