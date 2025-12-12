"""Data models for the supervisor system.

This module defines the core data types for service management:
- ServiceState: Lifecycle states for managed services
- ServiceEventType: Types of lifecycle events
- ServiceEvent: Immutable event records
- ServiceConfig: Service configuration
- ServiceStatus: Mutable runtime status
"""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path  # noqa: TC003 - Used in runtime type annotations


class ServiceState(StrEnum):
    """Service lifecycle states.

    States represent the current operational status of a managed service:
    - STOPPED: Service is not running
    - STARTING: Service is in the process of starting
    - RUNNING: Service is running normally
    - BACKOFF: Service crashed and is waiting before restart
    - FAILED: Service has exceeded max restarts and will not be restarted
    - DISABLED: Service has been explicitly disabled
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    BACKOFF = "backoff"
    FAILED = "failed"
    DISABLED = "disabled"


class ServiceEventType(StrEnum):
    """Types of service lifecycle events.

    Events are emitted when service state changes occur:
    - STARTED: Service process has been spawned
    - STOPPED: Service process has exited normally
    - CRASHED: Service process exited with non-zero code
    - RESTARTING: Service is being restarted after crash
    - DISABLED: Service has been disabled
    - OUTPUT: Service produced output (stdout/stderr)
    """

    STARTED = "started"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    DISABLED = "disabled"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True)
class ServiceEvent:
    """Immutable service lifecycle event.

    Events capture state changes and are emitted to OutputSinks for
    logging, monitoring, or UI updates.

    Attributes:
        service_name: Name of the service that generated the event.
        event_type: Type of lifecycle event.
        timestamp: ISO 8601 formatted timestamp.
        pid: Process ID if applicable.
        exit_code: Exit code if process terminated.
        message: Optional human-readable message.
    """

    service_name: str
    event_type: ServiceEventType
    timestamp: str
    pid: int | None = None
    exit_code: int | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    """Configuration for a managed service.

    Immutable configuration that defines how a service should be started,
    monitored, and restarted.

    Attributes:
        name: Unique identifier for the service.
        command: Command and arguments to execute.
        cwd: Working directory for the process.
        env: Additional environment variables.
        port: Port number the service listens on, if applicable.
        startup_timeout: Seconds to wait for service to start.
        shutdown_timeout: Seconds to wait for graceful shutdown.
        max_restarts: Maximum restart attempts before marking as failed.
        backoff_base: Base delay in seconds for exponential backoff.
        backoff_max: Maximum delay in seconds for backoff.
    """

    name: str
    command: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    port: int | None = None
    startup_timeout: float = 10.0
    shutdown_timeout: float = 5.0
    max_restarts: int = 5
    backoff_base: float = 1.0
    backoff_max: float = 60.0


@dataclass(slots=True)
class ServiceStatus:
    """Mutable runtime status of a service.

    Tracks the current state and history of a managed service. Updated
    as the service goes through its lifecycle.

    Attributes:
        state: Current service state.
        pid: Process ID of the running service, if any.
        restart_count: Number of times the service has been restarted.
        last_exit_code: Exit code from the last process termination.
        started_at: ISO 8601 timestamp of last start.
        stopped_at: ISO 8601 timestamp of last stop.
    """

    state: ServiceState = ServiceState.STOPPED
    pid: int | None = None
    restart_count: int = 0
    last_exit_code: int | None = None
    started_at: str | None = None
    stopped_at: str | None = None
