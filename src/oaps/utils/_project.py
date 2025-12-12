from ._paths import get_oaps_dir


def is_oaps_project() -> bool:
    """Check if the current Git worktree is an OAPS project."""
    oaps_dir = get_oaps_dir()
    return oaps_dir.is_dir()
