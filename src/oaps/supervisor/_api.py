"""FastAPI control endpoints for the supervisor.

This module provides REST API endpoints for controlling and monitoring
the supervisor and its managed services.
"""

# pyright: reportUnusedFunction=false
# FastAPI route handlers are registered via decorators, not direct calls

from typing import TYPE_CHECKING, Never

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from oaps.exceptions import ServiceNotFoundError, ServiceStartError, ServiceStopError

if TYPE_CHECKING:
    from ._supervisor import Supervisor


class ServiceStatusResponse(BaseModel):
    """Response model for service status."""

    name: str
    state: str
    pid: int | None
    restart_count: int
    last_exit_code: int | None
    started_at: str | None
    stopped_at: str | None


class SupervisorStatusResponse(BaseModel):
    """Response model for overall supervisor status."""

    services: dict[str, ServiceStatusResponse]
    total_services: int
    running_services: int


class MessageResponse(BaseModel):
    """Response model for simple message responses."""

    message: str


def _build_service_status(name: str, data: dict[str, object]) -> ServiceStatusResponse:
    """Build a ServiceStatusResponse from raw status data.

    Args:
        name: The service name.
        data: Raw status dictionary from supervisor.

    Returns:
        ServiceStatusResponse with properly typed fields.
    """
    pid = data.get("pid")
    restart_count = data.get("restart_count")
    last_exit_code = data.get("last_exit_code")
    started_at = data.get("started_at")
    stopped_at = data.get("stopped_at")
    state_val = data.get("state")

    return ServiceStatusResponse(
        name=name,
        state=str(state_val) if state_val is not None else "unknown",
        pid=int(pid) if isinstance(pid, int) else None,
        restart_count=int(restart_count) if isinstance(restart_count, int) else 0,
        last_exit_code=int(last_exit_code) if isinstance(last_exit_code, int) else None,
        started_at=str(started_at) if started_at else None,
        stopped_at=str(stopped_at) if stopped_at else None,
    )


def _raise_not_found(name: str, cause: ServiceNotFoundError) -> Never:
    """Raise HTTP 404 for service not found.

    Args:
        name: The service name.
        cause: The original exception.

    Raises:
        HTTPException: Always raises with 404 status.
    """
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Service '{name}' not found",
    ) from cause


def _raise_server_error(cause: Exception) -> Never:
    """Raise HTTP 500 for internal server error.

    Args:
        cause: The original exception.

    Raises:
        HTTPException: Always raises with 500 status.
    """
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(cause),
    ) from cause


def create_control_router(supervisor: Supervisor) -> APIRouter:  # noqa: PLR0915
    """Create a FastAPI router for supervisor control endpoints.

    Args:
        supervisor: The Supervisor instance to control.

    Returns:
        A FastAPI APIRouter with control endpoints.
    """
    router = APIRouter(prefix="/supervisor", tags=["supervisor"])

    @router.get("/status", response_model=SupervisorStatusResponse)
    async def get_supervisor_status() -> SupervisorStatusResponse:
        """Get overall supervisor status."""
        status_data = supervisor.get_status()
        services = {
            name: _build_service_status(name, data)
            for name, data in status_data.items()
        }

        running_count = sum(1 for s in services.values() if s.state == "running")

        return SupervisorStatusResponse(
            services=services,
            total_services=len(services),
            running_services=running_count,
        )

    @router.get("/services", response_model=list[ServiceStatusResponse])
    async def list_services() -> list[ServiceStatusResponse]:
        """List all managed services."""
        status_data = supervisor.get_status()
        return [_build_service_status(name, data) for name, data in status_data.items()]

    @router.get("/services/{name}", response_model=ServiceStatusResponse)
    async def get_service_status(name: str) -> ServiceStatusResponse:
        """Get status of a specific service."""
        try:
            service = supervisor.get_service(name)
        except ServiceNotFoundError as e:
            _raise_not_found(name, e)

        return ServiceStatusResponse(
            name=service.name,
            state=service.status.state.value,
            pid=service.status.pid,
            restart_count=service.status.restart_count,
            last_exit_code=service.status.last_exit_code,
            started_at=service.status.started_at,
            stopped_at=service.status.stopped_at,
        )

    @router.post("/services/{name}/start", response_model=MessageResponse)
    async def start_service(name: str) -> MessageResponse:
        """Start a specific service."""
        try:
            await supervisor.start_service(name)
        except ServiceNotFoundError as e:
            _raise_not_found(name, e)
        except ServiceStartError as e:
            _raise_server_error(e)

        return MessageResponse(message=f"Service '{name}' start requested")

    @router.post("/services/{name}/stop", response_model=MessageResponse)
    async def stop_service(name: str) -> MessageResponse:
        """Stop a specific service."""
        try:
            await supervisor.stop_service(name)
        except ServiceNotFoundError as e:
            _raise_not_found(name, e)
        except ServiceStopError as e:
            _raise_server_error(e)

        return MessageResponse(message=f"Service '{name}' stop requested")

    @router.post("/services/{name}/restart", response_model=MessageResponse)
    async def restart_service(name: str) -> MessageResponse:
        """Restart a specific service."""
        try:
            await supervisor.restart_service(name)
        except ServiceNotFoundError as e:
            _raise_not_found(name, e)
        except (ServiceStartError, ServiceStopError) as e:
            _raise_server_error(e)

        return MessageResponse(message=f"Service '{name}' restart requested")

    @router.post("/services/{name}/disable", response_model=MessageResponse)
    async def disable_service(name: str) -> MessageResponse:
        """Disable a specific service."""
        try:
            await supervisor.disable_service(name)
        except ServiceNotFoundError as e:
            _raise_not_found(name, e)

        return MessageResponse(message=f"Service '{name}' disabled")

    @router.post("/shutdown", response_model=MessageResponse)
    async def shutdown_supervisor() -> MessageResponse:
        """Trigger graceful shutdown of the supervisor."""
        await supervisor.shutdown()
        return MessageResponse(message="Shutdown initiated")

    return router
