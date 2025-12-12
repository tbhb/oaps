"""Output sink implementations for the supervisor system.

This module provides concrete implementations of the OutputSink protocol
for consuming and displaying service output and events.
"""

from typing import TYPE_CHECKING, Literal, final

from rich.console import Console
from rich.style import Style
from rich.text import Text

from ._models import ServiceEventType

if TYPE_CHECKING:
    from ._models import ServiceEvent


@final
class ConcatenatedOutputSink:
    """Output sink that writes to stdout with formatted prefixes.

    Formats service output as `[name:pid] line` with color coding:
    - stdout: Default styling
    - stderr: Dim red styling
    - Events: Special formatting based on event type
    """

    __slots__ = ("_console", "_event_styles", "_stderr_style", "_stdout_style")

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the output sink.

        Args:
            console: Rich Console instance for output. If None, creates a new one.
        """
        self._console = console or Console()
        self._stdout_style = Style()
        self._stderr_style = Style(color="red", dim=True)
        self._event_styles: dict[ServiceEventType, Style] = {
            ServiceEventType.STARTED: Style(color="green", bold=True),
            ServiceEventType.STOPPED: Style(color="yellow"),
            ServiceEventType.CRASHED: Style(color="red", bold=True),
            ServiceEventType.RESTARTING: Style(color="cyan"),
            ServiceEventType.DISABLED: Style(color="magenta", dim=True),
            ServiceEventType.OUTPUT: Style(dim=True),
        }

    async def write_line(
        self,
        service_name: str,
        pid: int,
        stream: Literal["stdout", "stderr"],
        line: str,
    ) -> None:
        """Write a line of service output with prefix.

        Args:
            service_name: Name of the service that produced the output.
            pid: Process ID of the service.
            stream: Which output stream the line came from.
            line: The output line (without trailing newline).
        """
        prefix = f"[{service_name}:{pid}]"
        style = self._stderr_style if stream == "stderr" else self._stdout_style

        text = Text()
        _ = text.append(prefix, style=Style(color="blue", bold=True))
        _ = text.append(" ")
        _ = text.append(line, style=style)

        self._console.print(text)

    async def write_event(
        self,
        service_name: str,
        event: ServiceEvent,
    ) -> None:
        """Write a service lifecycle event with special formatting.

        Args:
            service_name: Name of the service that generated the event.
            event: The lifecycle event to record.
        """
        style = self._event_styles.get(event.event_type, Style())

        text = Text()
        _ = text.append(f"[{service_name}]", style=Style(color="blue", bold=True))
        _ = text.append(" ")

        # Format event type
        event_label = event.event_type.value.upper()
        _ = text.append(event_label, style=style)

        # Add details based on event type
        if event.pid is not None:
            _ = text.append(f" (pid={event.pid})", style=Style(dim=True))

        if event.exit_code is not None:
            _ = text.append(f" exit_code={event.exit_code}", style=Style(dim=True))

        if event.message:
            _ = text.append(f" - {event.message}", style=style)

        self._console.print(text)
