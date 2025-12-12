"""Service manager for subprocess lifecycle management.

This module provides the ServiceManager class that handles spawning,
monitoring, and controlling subprocess services.
"""

import signal
import subprocess
from typing import TYPE_CHECKING, Literal, final

import anyio
import anyio.abc
from anyio.streams.text import TextReceiveStream

from oaps.exceptions import ServiceStartError, ServiceStopError

from ._models import (
    ServiceConfig,
    ServiceEvent,
    ServiceEventType,
    ServiceState,
    ServiceStatus,
)

if TYPE_CHECKING:
    from ._protocol import OutputSink


def _get_timestamp() -> str:
    """Get current timestamp in ISO 8601 format."""
    import pendulum  # noqa: PLC0415

    return pendulum.now("UTC").to_iso8601_string()


@final
class ServiceManager:
    """Manages the lifecycle of a subprocess service.

    Handles starting, stopping, and monitoring a single subprocess.
    Streams stdout/stderr to an OutputSink and tracks service state.

    Attributes:
        config: Immutable configuration for this service.
        status: Mutable runtime status tracking.
    """

    __slots__ = (
        "_cancel_scope",
        "_lock",
        "_output_sink",
        "_process",
        "config",
        "status",
    )

    def __init__(
        self,
        config: ServiceConfig,
        output_sink: OutputSink,
    ) -> None:
        """Initialize the service manager.

        Args:
            config: Configuration for the service.
            output_sink: Sink for service output and events.
        """
        self.config = config
        self.status = ServiceStatus()
        self._output_sink = output_sink
        self._process: anyio.abc.Process | None = None
        self._cancel_scope: anyio.CancelScope | None = None
        self._lock = anyio.Lock()

    @property
    def name(self) -> str:
        """Return the unique name of this service."""
        return self.config.name

    @property
    def state(self) -> ServiceState:
        """Return the current state of this service."""
        return self.status.state

    @property
    def pid(self) -> int | None:
        """Return the process ID if running, None otherwise."""
        return self.status.pid

    async def emit_event(
        self,
        event_type: ServiceEventType,
        *,
        message: str | None = None,
        exit_code: int | None = None,
    ) -> None:
        """Emit a service lifecycle event to the output sink.

        Args:
            event_type: Type of event to emit.
            message: Optional message for the event.
            exit_code: Exit code if process terminated.
        """
        event = ServiceEvent(
            service_name=self.name,
            event_type=event_type,
            timestamp=_get_timestamp(),
            pid=self.status.pid,
            exit_code=exit_code,
            message=message,
        )
        try:  # noqa: SIM105
            await self._output_sink.write_event(self.name, event)
        except Exception:  # noqa: BLE001, S110
            # Output sink errors should not crash the service
            pass

    async def _stream_output(
        self,
        stream: TextReceiveStream,
        stream_name: Literal["stdout", "stderr"],
    ) -> None:
        """Stream output from a text stream to the output sink.

        Args:
            stream: The text stream to read from.
            stream_name: Name of the stream ("stdout" or "stderr").
        """
        try:
            async for raw_line in stream:
                # Remove trailing newline if present
                clean_line = raw_line.rstrip("\n\r")
                if self.status.pid is not None:
                    try:  # noqa: SIM105
                        await self._output_sink.write_line(
                            self.name,
                            self.status.pid,
                            stream_name,
                            clean_line,
                        )
                    except Exception:  # noqa: BLE001, S110
                        # Output sink errors should not crash streaming
                        pass
        except anyio.ClosedResourceError:
            # Stream closed, which is expected on process exit
            pass

    async def start(self) -> None:
        """Start the service subprocess.

        Spawns the subprocess and begins streaming output. Does not wait
        for the process to complete - use wait() for that.

        Raises:
            ServiceStartError: If the service fails to start.
        """
        if self.status.state == ServiceState.RUNNING:
            return

        self.status.state = ServiceState.STARTING
        self.status.started_at = _get_timestamp()

        try:
            # Build environment
            env: dict[str, str] | None = None
            if self.config.env:
                import os  # noqa: PLC0415

                env = {**os.environ, **self.config.env}

            # Start the process
            self._process = await anyio.open_process(
                self.config.command,
                cwd=self.config.cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.status.pid = self._process.pid
            self.status.state = ServiceState.RUNNING

            await self.emit_event(
                ServiceEventType.STARTED,
                message=f"Started with command: {' '.join(self.config.command)}",
            )

        except OSError as e:
            self.status.state = ServiceState.FAILED
            msg = f"Failed to start service '{self.name}': {e}"
            raise ServiceStartError(msg, service_name=self.name, cause=e) from e

    async def run(self) -> int:
        """Run the service and stream its output until completion.

        Starts the service if not already running and waits for it to
        complete while streaming output.

        Returns:
            The process exit code.

        Raises:
            ServiceStartError: If the service fails to start.
        """
        if self.status.state != ServiceState.RUNNING:
            await self.start()

        if self._process is None:
            msg = f"Service '{self.name}' process is None after start"
            raise ServiceStartError(msg, service_name=self.name)

        exit_code: int = 0

        try:
            # Stream stdout and stderr concurrently
            async with anyio.create_task_group() as tg:
                if self._process.stdout is not None:
                    stdout_stream = TextReceiveStream(self._process.stdout)
                    tg.start_soon(self._stream_output, stdout_stream, "stdout")

                if self._process.stderr is not None:
                    stderr_stream = TextReceiveStream(self._process.stderr)
                    tg.start_soon(self._stream_output, stderr_stream, "stderr")

                # Wait for process to complete
                exit_code = await self._process.wait()

            self.status.last_exit_code = exit_code
            self.status.stopped_at = _get_timestamp()

            if exit_code == 0:
                self.status.state = ServiceState.STOPPED
                await self.emit_event(
                    ServiceEventType.STOPPED,
                    exit_code=exit_code,
                    message="Exited normally",
                )
            else:
                self.status.state = ServiceState.STOPPED
                await self.emit_event(
                    ServiceEventType.CRASHED,
                    exit_code=exit_code,
                    message=f"Exited with code {exit_code}",
                )

        finally:
            # Ensure cleanup happens even on cancellation
            self.status.pid = None
            self._process = None

        return exit_code

    async def stop(self, graceful_timeout: float | None = None) -> None:
        """Stop the service gracefully.

        Sends SIGTERM and waits for graceful shutdown. If the process
        doesn't exit within the timeout, sends SIGKILL.

        Args:
            graceful_timeout: Seconds to wait for graceful shutdown.
                Uses config default if None.

        Raises:
            ServiceStopError: If the service fails to stop cleanly.
        """
        if self._process is None:
            self.status.state = ServiceState.STOPPED
            return

        actual_timeout = (
            graceful_timeout
            if graceful_timeout is not None
            else self.config.shutdown_timeout
        )

        try:
            # Send SIGTERM for graceful shutdown
            self._process.send_signal(signal.SIGTERM)

            # Wait for process to exit with timeout
            with anyio.move_on_after(actual_timeout):
                _ = await self._process.wait()

            # Check if process is still running
            if self._process.returncode is None:
                # Process didn't exit, force kill
                self._process.kill()
                _ = await self._process.wait()

            self.status.last_exit_code = self._process.returncode
            self.status.stopped_at = _get_timestamp()
            self.status.state = ServiceState.STOPPED
            self.status.pid = None

            await self.emit_event(
                ServiceEventType.STOPPED,
                exit_code=self.status.last_exit_code,
                message="Stopped by request",
            )

        except ProcessLookupError:
            # Process already exited
            self.status.state = ServiceState.STOPPED
            self.status.pid = None

        except OSError as e:
            msg = f"Failed to stop service '{self.name}': {e}"
            raise ServiceStopError(msg, service_name=self.name, cause=e) from e

        finally:
            self._process = None

    async def disable(self) -> None:
        """Disable the service, preventing automatic restarts.

        Stops the service if running and marks it as disabled.
        """
        if self.status.state == ServiceState.RUNNING:
            await self.stop()

        self.status.state = ServiceState.DISABLED
        await self.emit_event(
            ServiceEventType.DISABLED,
            message="Service disabled",
        )

    def is_running(self) -> bool:
        """Check if the service is currently running."""
        return self.status.state == ServiceState.RUNNING and self._process is not None
