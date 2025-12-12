"""Main supervisor coordinator for managing multiple services.

This module provides the Supervisor class that coordinates multiple
ServiceManagers using anyio for structured concurrency.
"""

import signal
from typing import TYPE_CHECKING, final

import anyio
import anyio.abc

from oaps.exceptions import ServiceNotFoundError

from ._backoff import ExponentialBackoff
from ._models import ServiceConfig, ServiceEventType, ServiceState
from ._output import ConcatenatedOutputSink
from ._service import ServiceManager

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ._protocol import OutputSink


@final
class Supervisor:
    """Coordinates multiple subprocess services.

    Manages a collection of ServiceManagers, handling startup, shutdown,
    and restart logic. Uses anyio task groups for structured concurrency.

    Each service runs in its own task with automatic restart on crash,
    using exponential backoff to prevent rapid restart loops.
    """

    __slots__ = (
        "_backoffs",
        "_output_sink",
        "_services",
        "_shutdown_event",
        "_task_group",
    )

    def __init__(
        self,
        configs: Sequence[ServiceConfig],
        output_sink: OutputSink | None = None,
    ) -> None:
        """Initialize the supervisor.

        Args:
            configs: Configurations for services to manage.
            output_sink: Sink for service output. Uses ConcatenatedOutputSink if None.
        """
        self._output_sink: OutputSink = output_sink or ConcatenatedOutputSink()
        self._services: dict[str, ServiceManager] = {}
        self._backoffs: dict[str, ExponentialBackoff] = {}
        self._shutdown_event: anyio.Event | None = None
        self._task_group: anyio.abc.TaskGroup | None = None

        # Create service managers
        for config in configs:
            self._services[config.name] = ServiceManager(config, self._output_sink)
            self._backoffs[config.name] = ExponentialBackoff(
                base=config.backoff_base,
                max_delay=config.backoff_max,
            )

    @property
    def services(self) -> dict[str, ServiceManager]:
        """Return the dictionary of managed services."""
        return self._services

    def get_service(self, name: str) -> ServiceManager:
        """Get a service by name.

        Args:
            name: The service name.

        Returns:
            The ServiceManager for the named service.

        Raises:
            ServiceNotFoundError: If no service exists with that name.
        """
        service = self._services.get(name)
        if service is None:
            msg = f"Service '{name}' not found"
            raise ServiceNotFoundError(msg, service_name=name)
        return service

    async def _run_service_with_restart(
        self,
        service: ServiceManager,
    ) -> None:
        """Run a service with automatic restart on crash.

        Implements the restart loop with exponential backoff.

        Args:
            service: The service to run.
        """
        backoff = self._backoffs[service.name]
        config = service.config

        while True:
            if self._should_stop_restart_loop(service, config):
                break

            try:
                exit_code = await service.run()

                # Check if this is a normal exit (code 0) or we're shutting down
                if exit_code == 0:
                    break

                if self._shutdown_event is not None and self._shutdown_event.is_set():
                    break

                # Service crashed, prepare for restart
                await self._handle_service_crash(service, config, backoff)

            except anyio.get_cancelled_exc_class():
                # Task was cancelled, stop the service
                await service.stop()
                break

    def _should_stop_restart_loop(
        self,
        service: ServiceManager,
        config: ServiceConfig,
    ) -> bool:
        """Check if the restart loop should stop.

        Args:
            service: The service being managed.
            config: The service configuration.

        Returns:
            True if the loop should stop, False otherwise.
        """
        # Check if we should stop
        if self._shutdown_event is not None and self._shutdown_event.is_set():
            return True

        # Check if service is disabled
        if service.status.state == ServiceState.DISABLED:
            return True

        # Check if we've exceeded max restarts
        return service.status.restart_count >= config.max_restarts

    async def _handle_service_crash(
        self,
        service: ServiceManager,
        config: ServiceConfig,
        backoff: ExponentialBackoff,
    ) -> None:
        """Handle a service crash by preparing for restart.

        Args:
            service: The service that crashed.
            config: The service configuration.
            backoff: The backoff calculator.
        """
        service.status.restart_count += 1
        service.status.state = ServiceState.BACKOFF

        # Calculate backoff delay
        delay = backoff.delay(service.status.restart_count - 1)

        restart_count = service.status.restart_count
        max_restarts = config.max_restarts
        msg = f"Restarting in {delay:.1f}s (attempt {restart_count}/{max_restarts})"
        await service.emit_event(
            ServiceEventType.RESTARTING,
            message=msg,
        )

        # Wait before restart (interruptible by shutdown)
        with anyio.move_on_after(delay):
            if self._shutdown_event is not None:
                await self._shutdown_event.wait()

    async def start_service(self, name: str) -> None:
        """Start a specific service.

        Args:
            name: The service name.

        Raises:
            ServiceNotFoundError: If no service exists with that name.
            ServiceStartError: If the service fails to start.
        """
        service = self.get_service(name)

        # Reset state if needed
        if service.status.state in (ServiceState.FAILED, ServiceState.DISABLED):
            service.status.state = ServiceState.STOPPED
            service.status.restart_count = 0

        # Start in task group if running
        if self._task_group is not None:
            self._task_group.start_soon(self._run_service_with_restart, service)
        else:
            await service.start()

    async def stop_service(
        self,
        name: str,
        graceful_timeout: float | None = None,
    ) -> None:
        """Stop a specific service.

        Args:
            name: The service name.
            graceful_timeout: Seconds to wait for graceful shutdown.

        Raises:
            ServiceNotFoundError: If no service exists with that name.
            ServiceStopError: If the service fails to stop.
        """
        service = self.get_service(name)
        await service.stop(graceful_timeout)

    async def restart_service(self, name: str) -> None:
        """Restart a specific service.

        Args:
            name: The service name.

        Raises:
            ServiceNotFoundError: If no service exists with that name.
        """
        service = self.get_service(name)

        # Stop if running
        if service.is_running():
            await service.stop()

        # Reset restart count on manual restart
        service.status.restart_count = 0

        # Start the service
        await self.start_service(name)

    async def disable_service(self, name: str) -> None:
        """Disable a specific service.

        Args:
            name: The service name.

        Raises:
            ServiceNotFoundError: If no service exists with that name.
        """
        service = self.get_service(name)
        await service.disable()

    async def run(self) -> None:
        """Run the supervisor, starting all services.

        Blocks until shutdown is triggered (via signal or shutdown()).
        Uses structured concurrency to manage service tasks.
        """
        self._shutdown_event = anyio.Event()

        # Set up signal handlers
        async def handle_signals() -> None:
            with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
                async for signum in signals:
                    if signum in (signal.SIGINT, signal.SIGTERM):
                        if self._shutdown_event is not None:
                            self._shutdown_event.set()
                        break

        async with anyio.create_task_group() as tg:
            self._task_group = tg

            # Start signal handler
            tg.start_soon(handle_signals)

            # Start all services
            for service in self._services.values():
                if service.status.state != ServiceState.DISABLED:
                    tg.start_soon(self._run_service_with_restart, service)

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel all service tasks first to stop restart loops
            tg.cancel_scope.cancel()

        # Now stop services outside the task group to avoid races
        self._task_group = None
        for service in self._services.values():
            if service.is_running():
                await service.stop()

    async def shutdown(self) -> None:
        """Trigger graceful shutdown of all services.

        Sets the shutdown event, which will cause run() to begin
        stopping services and exit.
        """
        if self._shutdown_event is not None:
            self._shutdown_event.set()

    def get_status(self) -> dict[str, dict[str, object]]:
        """Get status summary for all services.

        Returns:
            Dictionary mapping service names to status dictionaries.
        """
        return {
            name: {
                "state": service.status.state.value,
                "pid": service.status.pid,
                "restart_count": service.status.restart_count,
                "last_exit_code": service.status.last_exit_code,
                "started_at": service.status.started_at,
                "stopped_at": service.status.stopped_at,
            }
            for name, service in self._services.items()
        }
