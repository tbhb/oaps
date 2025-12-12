"""Control application factory for the start command.

This module provides a factory function for creating the in-process
FastAPI control application that exposes supervisor control endpoints.
"""

from typing import TYPE_CHECKING

from fastapi import FastAPI

from oaps.supervisor import create_control_router

if TYPE_CHECKING:
    from oaps.supervisor import Supervisor


def create_control_app(supervisor: Supervisor) -> FastAPI:
    """Create the FastAPI control application.

    Creates a minimal FastAPI app with the supervisor control router
    mounted for managing services.

    Args:
        supervisor: The Supervisor instance to control.

    Returns:
        A FastAPI application with supervisor control endpoints.
    """
    app = FastAPI(
        title="OAPS Control",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    control_router = create_control_router(supervisor)
    app.include_router(control_router)

    return app
