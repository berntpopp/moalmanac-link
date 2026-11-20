"""End-to-end MCP tool tests through an in-memory FastMCP client."""

from __future__ import annotations

from typing import Any

from fastmcp import Client

from moalmanac_link.mcp.capabilities import TOOLS


async def _raw(mcp: Any, name: str, args: dict[str, Any]) -> Any:
    async with Client(mcp) as client:
        return await client.call_tool(name, args, raise_on_error=False)


async def test_registered_tools_match_capabilities_and_are_documented(facade: Any) -> None:
    async with Client(facade) as client:
        tools = await client.list_tools()
    assert [t.name for t in tools] == TOOLS
    for tool in tools:
        props = tool.input_schema.get("properties", {})
        for name, prop in props.items():
            assert prop.get("description"), f"{tool.name}.{name} lacks a description"
        for name in tool.input_schema.get("required", []):
            assert props[name].get("examples"), f"{tool.name}.{name} lacks examples"
        assert tool.description and "Signature:" in tool.description
        assert tool.annotations is not None and tool.annotations.read_only_hint is True
        assert tool.output_schema is None


async def test_search_envelope_and_next_steps(facade: Any, call_tool: Any) -> None:
    out = await call_tool(
        facade, "search_approvals", {"gene": "KRAS", "biomarker": "G12C", "disease": "NSCLC"}
    )
    assert out["success"] is True and out["total"] >= 4 and out["truncated"] is False
    assert out["source"]["license"] == "CC-BY-4.0" and out["data_version"] == "v.2026-11-05"
    meta = out["_meta"]
    assert meta["tool"] == "search_approvals" and meta["source"] == "moalmanac"
    assert meta["unsafe_for_clinical_use"] is True
    assert meta["next_commands"][0]["tool"] == "get_indication"


async def test_empty_search_points_at_the_vocabulary(facade: Any, call_tool: Any) -> None:
    out = await call_tool(
        facade, "search_approvals", {"therapy": "sotorasib", "disease": "colorectal"}
    )
    assert out["success"] is True and out["total"] == 0
    assert out["message"].startswith("No MOAlmanac approval found")
    assert out["_meta"]["next_commands"][0]["tool"] == "list_biomarkers"


async def test_unknown_indication_is_is_error_not_found(facade: Any) -> None:
    res = await _raw(facade, "get_indication", {"indication_id": "ind:fda:nope:0"})
    assert res.is_error is True
    body = res.structured_content
    assert body["error_code"] == "not_found" and body["field"] == "indication_id"
    assert body["_meta"]["next_commands"] == [{"tool": "search_approvals", "arguments": {}}]


async def test_unknown_filter_is_not_found_naming_it(facade: Any) -> None:
    res = await _raw(facade, "search_approvals", {"disease": "__no_such_disease__"})
    body = res.structured_content
    assert res.is_error is True and body["error_code"] == "not_found"
    assert body["field"] == "disease" and "__no_such" not in body["message"]


async def test_variant_in_gene_is_rejected_with_a_converter(facade: Any) -> None:
    res = await _raw(facade, "search_approvals", {"gene": "BRAF V600E"})
    body = res.structured_content
    assert res.is_error is True and body["error_code"] == "invalid_input"
    assert body["field"] == "gene" and body["allowed_values"]
    assert body["_meta"]["next_commands"] == [{"tool": "list_biomarkers", "arguments": {}}]


async def test_over_cap_limit_suggests_the_clamped_call(facade: Any) -> None:
    args = {"gene": "BRAF", "limit": 500}
    res = await _raw(facade, "search_approvals", args)
    assert res.is_error is True
    assert res.structured_content["_meta"]["next_commands"] == [
        {"tool": "search_approvals", "arguments": {**args, "limit": 100}}
    ]


async def test_wrong_case_enum_suggests_the_matching_value(facade: Any) -> None:
    args = {"gene": "KRAS", "agency": "FDA"}
    res = await _raw(facade, "search_approvals", args)
    assert res.is_error is True
    assert res.structured_content["_meta"]["next_commands"] == [
        {"tool": "search_approvals", "arguments": {**args, "agency": "fda"}}
    ]


async def test_capabilities_and_diagnostics(facade: Any, call_tool: Any) -> None:
    caps = await call_tool(facade, "get_server_capabilities", {})
    assert caps["tools"] == TOOLS and caps["research_use_only"] is True
    assert "not a clinical actionability report" in caps["research_use_notice"].lower()
    assert len(caps["known_upstream_defects"]) == 7
    assert caps["release"]["doi"] == "10.5281/zenodo.23986188"
    diag = await call_tool(facade, "get_diagnostics", {})
    assert diag["snapshot"]["data_version"] == "v.2026-11-05"
    assert diag["snapshot"]["approvals"] == caps["release"]["counts"]["approvals"]


async def test_descriptions_name_only_returned_fields(facade: Any, call_tool: Any) -> None:
    """Contract truth: the fields a description promises are in the response."""
    out = await call_tool(facade, "search_approvals", {"gene": "BRAF", "limit": 1})
    row = out["approvals"][0]
    assert {"agency", "status", "biomarkers", "genes", "disease", "therapies", "label"} <= set(row)
    assert {"ncit", "oncotree"} <= set(row["disease"])
    assert {"document_id", "version_date", "regulatory_id"} <= set(row["label"])
    ind = await call_tool(facade, "get_indication", {"indication_id": row["indication_id"]})
    assert {"status", "description", "contributions", "documents"} <= set(ind["indication"])
    assert {"brand", "generic", "company", "version_date", "regulatory_id", "url"} <= set(
        ind["indication"]["documents"][0]
    )
    bms = await call_tool(facade, "list_biomarkers", {"gene": "EGFR"})
    assert {"name", "type", "genes", "approvals"} <= set(bms["biomarkers"][0])
