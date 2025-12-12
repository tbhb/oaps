"""Context composition for template rendering."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(slots=True, frozen=True)
class BaseContext:
    """Typed base context for template rendering.

    Provides common context values available to all templates:
    - today: Current date
    - author_name: Author name from environment or git config
    - author_email: Author email from environment or git config
    - tool_versions: Detected tool versions in the project
    """

    today: date
    author_name: str | None
    author_email: str | None
    tool_versions: dict[str, str | None]


def get_base_context() -> BaseContext:
    """Build base context with auto-detected values.

    Returns a BaseContext with:
    - today: Current date
    - author_name: Author name from env or git config
    - author_email: Author email from env or git config
    - tool_versions: Detected tool versions

    Returns:
        BaseContext with auto-detected values.
    """
    from oaps.utils._author import get_author_info  # noqa: PLC0415
    from oaps.utils._detect import detect_tooling  # noqa: PLC0415

    author = get_author_info()
    return BaseContext(
        today=datetime.now(tz=UTC).date(),
        author_name=author.name,
        author_email=author.email,
        tool_versions=detect_tooling(),
    )


def compose_context(
    base: Mapping[str, object] | BaseContext,
    component: Mapping[str, object] | None = None,
    user: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose a final context from multiple layers.

    Context is merged in order (later values override earlier):
    1. Base context (always present)
    2. Component-specific context (e.g., SpecContext fields)
    3. User-provided context (flat dict from CLI or API)

    Args:
        base: The base context from get_base_context() or a dict.
        component: Optional component-specific context.
        user: Optional user-provided key-value pairs.

    Returns:
        A merged context dictionary.
    """
    # Convert dataclass to dict if needed
    result: dict[str, object] = (
        dict(asdict(base)) if isinstance(base, BaseContext) else dict(base)
    )
    if component:
        result = {**result, **component}
    if user:
        result = {**result, **user}
    return result
