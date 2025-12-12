"""Protocol definitions for the supervisor system.

This module defines the interfaces that enable decoupling between
the supervisor core and output/UI implementations:
- OutputSink: Protocol for consuming service output and events
- ServiceProtocol: Protocol for managed services
"""

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ._models import ServiceEvent, ServiceState


@runtime_checkable
class OutputSink(Protocol):
    """Protocol for consuming service output lines.

    OutputSinks receive output from managed services and can format,
    store, or display it. The protocol is async to support non-blocking
    I/O operations like writing to files or updating UIs.

    Implementations must handle:
    - Service output lines (stdout/stderr)
    - Service lifecycle events
    """

    async def write_line(
        self,
        service_name: str,
        pid: int,
        stream: Literal["stdout", "stderr"],
        line: str,
    ) -> None:
        """Write a line of service output.

        Args:
            service_name: Name of the service that produced the output.
            pid: Process ID of the service.
            stream: Which output stream the line came from.
            line: The output line (without trailing newline).
        """
        ...

    async def write_event(
        self,
        service_name: str,
        event: ServiceEvent,
    ) -> None:
        """Write a service lifecycle event.

        Args:
            service_name: Name of the service that generated the event.
            event: The lifecycle event to record.
        """
        ...


@runtime_checkable
class ServiceProtocol(Protocol):
    """Protocol for managed services.

    Defines the minimal interface required to manage a service's
    lifecycle. Used by the Supervisor to interact with ServiceManager
    instances without tight coupling.
    """

    @property
    def name(self) -> str:
        """Return the unique name of this service."""
        ...

    @property
    def state(self) -> ServiceState:
        """Return the current state of this service."""
        ...

    @property
    def pid(self) -> int | None:
        """Return the process ID if running, None otherwise."""
        ...

    async def start(self) -> None:
        """Start the service.

        Raises:
            ServiceStartError: If the service fails to start.
        """
        ...

    async def stop(self, graceful_timeout: float = 5.0) -> None:
        """Stop the service gracefully.

        Args:
            graceful_timeout: Seconds to wait for graceful shutdown before force kill.

        Raises:
            ServiceStopError: If the service fails to stop cleanly.
        """
        ...
