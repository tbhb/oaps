# pyright: reportAny=false
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, cast

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ._api import api_router
from ._pages import router as pages_router

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


def _get_docs_port() -> int | None:
    """Get the docs server port from environment variable.

    Returns:
        The docs port, or None if not configured.
    """
    port_str = os.environ.get("OAPS_DOCS_PORT")
    if port_str is None:
        return None
    try:
        return int(port_str)
    except ValueError:
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage app lifespan, including httpx client for docs proxy.

    Args:
        app: The FastAPI application.

    Yields:
        None
    """
    docs_port = _get_docs_port()
    if docs_port is not None:
        app.state.docs_client = httpx.AsyncClient(
            base_url=f"http://localhost:{docs_port}"
        )
    else:
        app.state.docs_client = None
    yield
    docs_client: httpx.AsyncClient | None = getattr(app.state, "docs_client", None)
    if docs_client is not None:
        await docs_client.aclose()


app = FastAPI(docs_url=None, redoc_url="/api-docs", lifespan=lifespan)
app.include_router(router=api_router)
app.include_router(router=pages_router)


async def _stream_and_close(response: httpx.Response) -> AsyncGenerator[bytes]:
    """Stream response bytes and ensure the response is closed.

    Args:
        response: The httpx response to stream.

    Yields:
        Response body chunks.
    """
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    finally:
        await response.aclose()


@retry(
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
    reraise=True,
)
async def _proxy_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
) -> httpx.Response:
    """Make a proxied request with retry logic.

    Args:
        client: The httpx client to use.
        method: HTTP method.
        url: Target URL.
        headers: Request headers.

    Returns:
        The httpx response.

    Raises:
        httpx.ConnectError: If connection fails after retries.
        httpx.TimeoutException: If request times out after retries.
    """
    return await client.request(method=method, url=url, headers=headers)


@app.api_route(
    "/docs/{path:path}",
    methods=["GET", "HEAD", "OPTIONS"],
    include_in_schema=False,
)
async def proxy_docs(path: str, request: Request) -> Response:
    """Proxy requests to the docs server.

    Args:
        path: The path after /docs/ to proxy.
        request: The incoming request.

    Returns:
        The proxied response from the docs server.
    """
    docs_client: httpx.AsyncClient | None = cast(
        "httpx.AsyncClient | None",
        getattr(request.app.state, "docs_client", None),
    )
    if docs_client is None:
        return Response(
            content="Documentation server not configured",
            status_code=503,
            media_type="text/plain",
        )

    # Build the target URL
    target_path = f"/{path}" if path else "/"
    if request.url.query:
        target_path = f"{target_path}?{request.url.query}"

    # Forward the request with retries
    try:
        proxy_response = await _proxy_request(
            client=docs_client,
            method=request.method,
            url=target_path,
            headers={
                key: value
                for key, value in request.headers.items()
                if key.lower() not in ("host", "connection")
            },
        )
    except (httpx.ConnectError, httpx.TimeoutException):
        return Response(
            content="Documentation server unavailable",
            status_code=503,
            media_type="text/plain",
        )

    # Return as streaming response for efficiency
    content_type_header = cast("str | None", proxy_response.headers.get("content-type"))
    return StreamingResponse(
        content=_stream_and_close(proxy_response),
        status_code=proxy_response.status_code,
        headers={
            key: value
            for key, value in proxy_response.headers.items()
            if key.lower()
            not in ("content-encoding", "transfer-encoding", "connection")
        },
        media_type=content_type_header,
    )
