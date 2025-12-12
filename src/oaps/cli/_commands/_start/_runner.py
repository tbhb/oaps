"""Async runner for the start command.

This module provides the async entry point that coordinates running
the supervisor and control app together using anyio.
"""

from typing import TYPE_CHECKING

import anyio
import uvicorn

from oaps.supervisor import ConcatenatedOutputSink, Supervisor

from ._app import create_control_app

if TYPE_CHECKING:
    from collections.abc import Sequence

    from oaps.supervisor import ServiceConfig


async def run_start(
    configs: Sequence[ServiceConfig],
    control_port: int,
) -> None:
    """Run the supervisor with services and control app.

    Starts the supervisor managing all configured services, plus an
    in-process control API for managing the supervisor.

    Args:
        configs: Service configurations for the supervisor.
        control_port: Port for the control API server.
    """
    output_sink = ConcatenatedOutputSink()
    supervisor = Supervisor(list(configs), output_sink)
    control_app = create_control_app(supervisor)

    # Configure uvicorn for the control server
    uvicorn_config = uvicorn.Config(
        app=control_app,
        host="127.0.0.1",
        port=control_port,
        log_level="warning",
        access_log=False,
    )
    control_server = uvicorn.Server(uvicorn_config)

    async with anyio.create_task_group() as tg:
        # Start the control server first so it's ready before services start
        tg.start_soon(control_server.serve)

        # Give the control server a moment to start
        await anyio.sleep(0.1)

        # Run the supervisor (blocks until shutdown)
        await supervisor.run()

        # Supervisor has shut down, stop the control server
        control_server.should_exit = True
