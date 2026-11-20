"""Discovery tools: ``get_server_capabilities`` and ``get_diagnostics`` (zero-arg)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from moalmanac_link import snapshot
from moalmanac_link.buildinfo import build_info
from moalmanac_link.mcp import metrics
from moalmanac_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from moalmanac_link.mcp.capabilities import build_capabilities, capabilities_version
from moalmanac_link.mcp.envelope import McpErrorContext, ToolReturn, run_mcp_tool
from moalmanac_link.mcp.next_commands import cmd
from moalmanac_link.mcp.service_adapters import get_moa_service

if TYPE_CHECKING:
    from fastmcp import FastMCP

_FIRST_STEP = cmd("search_approvals", gene="KRAS", biomarker="G12C", disease="NSCLC")


def register_discovery_tools(mcp: FastMCP) -> None:
    """Register the discovery tools on a FastMCP instance."""

    @mcp.tool(
        name="get_server_capabilities",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"discovery"},
        description=(
            "Describe this server: identifiers, agencies, limits, data version (release tag, "
            "commit, DOI), known upstream defects, licence, citation and error codes. "
            "Signature: get_server_capabilities()."
        ),
    )
    async def get_server_capabilities() -> ToolReturn:
        async def call() -> dict[str, Any]:
            payload = build_capabilities()
            payload["_meta"] = {"next_commands": [_FIRST_STEP]}
            return payload

        return await run_mcp_tool(
            "get_server_capabilities", call, context=McpErrorContext("get_server_capabilities")
        )

    @mcp.tool(
        name="get_diagnostics",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"discovery"},
        description=(
            "Report runtime state: build, the bundled snapshot's release, commit and "
            "sha256, and tool latency metrics. "
            "Signature: get_diagnostics()."
        ),
    )
    async def get_diagnostics() -> ToolReturn:
        async def call() -> dict[str, Any]:
            prov = snapshot.provenance()
            return {
                "build": build_info(),
                "snapshot": {
                    "data_version": prov["data_version"],
                    "source_commit": prov["source_commit"],
                    "derived_sha256": prov["derived_sha256"],
                    "approvals": len(get_moa_service().data["approvals"]),
                },
                "metrics": metrics.snapshot(),
                "capabilities_version": capabilities_version(),
                "_meta": {"next_commands": [cmd("get_server_capabilities"), _FIRST_STEP]},
            }

        return await run_mcp_tool(
            "get_diagnostics", call, context=McpErrorContext("get_diagnostics")
        )
