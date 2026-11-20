"""Shared fixtures: a real MoaService over the bundled snapshot (network-free).

``facade`` wires the service into a real FastMCP instance and ``call_tool`` drives it
through an in-memory ``fastmcp.Client``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import Any

import pytest

from moalmanac_link.mcp import metrics
from moalmanac_link.mcp.facade import create_moa_mcp
from moalmanac_link.mcp.service_adapters import set_moa_service
from moalmanac_link.service import MoaService


@pytest.fixture(autouse=True)
def _reset_metrics() -> Iterator[None]:
    """Keep the process-wide metrics collector clean between tests."""
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture(scope="session")
def moa_service() -> MoaService:
    """A real MoaService over the bundled, verified snapshot."""
    return MoaService()


@pytest.fixture
def facade(moa_service: MoaService) -> Iterator[Any]:
    """A FastMCP facade with the service injected; cleans up after."""
    mcp = create_moa_mcp(service_factory=lambda: moa_service)
    yield mcp
    set_moa_service(None)


@pytest.fixture
def call_tool() -> Callable[[Any, str, dict[str, Any]], Awaitable[Any]]:
    """Call a tool through an in-memory ``fastmcp.Client``; return the structured dict."""
    from fastmcp import Client

    async def _call(mcp: Any, name: str, args: dict[str, Any]) -> Any:
        async with Client(mcp) as client:
            res = await client.call_tool(name, args, raise_on_error=False)
        if isinstance(res.structured_content, dict):
            return res.structured_content
        return res.data

    return _call
