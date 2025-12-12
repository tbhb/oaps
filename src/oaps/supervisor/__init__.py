"""Supervisor package for managing subprocess services.

This package provides a comprehensive solution for managing multiple
subprocess services with structured concurrency, automatic restarts,
and control APIs.

Key Components:
    - ServiceConfig: Configuration for managed services
    - ServiceState: Lifecycle state enumeration
    - ServiceStatus: Runtime status tracking
    - ServiceEvent: Lifecycle event records
    - OutputSink: Protocol for output consumption
    - ConcatenatedOutputSink: Console output implementation
    - ExponentialBackoff: Retry delay calculator
    - ServiceManager: Single service lifecycle manager
    - Supervisor: Multi-service coordinator
    - create_control_router: FastAPI endpoint factory

Example:
    >>> from oaps.supervisor import ServiceConfig, Supervisor
    >>> configs = [
    ...     ServiceConfig(name="api", command=("uvicorn", "app:app")),
    ...     ServiceConfig(name="worker", command=("python", "worker.py")),
    ... ]
    >>> supervisor = Supervisor(configs)
    >>> await supervisor.run()  # Blocks until shutdown
"""

from ._api import create_control_router
from ._backoff import ExponentialBackoff
from ._models import (
    ServiceConfig,
    ServiceEvent,
    ServiceEventType,
    ServiceState,
    ServiceStatus,
)
from ._output import ConcatenatedOutputSink
from ._protocol import OutputSink, ServiceProtocol
from ._service import ServiceManager
from ._supervisor import Supervisor

__all__ = [
    "ConcatenatedOutputSink",
    "ExponentialBackoff",
    "OutputSink",
    "ServiceConfig",
    "ServiceEvent",
    "ServiceEventType",
    "ServiceManager",
    "ServiceProtocol",
    "ServiceState",
    "ServiceStatus",
    "Supervisor",
    "create_control_router",
]
