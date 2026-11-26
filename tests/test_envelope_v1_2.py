"""Response-Envelope Standard v1.2: every data tool result validates against the schema.

The schema is vendored from berntpopp/genefoundry-envelope, tag v1.2.0.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any

import jsonschema
import pytest

from moalmanac_link import snapshot
from moalmanac_link.mcp.capabilities import TOOLS

SCHEMA_PATH = pathlib.Path(__file__).parent / "conformance" / "envelope-v1.2.schema.json"
SCHEMA_SHA256 = "c3c47e20d7dd189aac2568fc963b5514d7a5ac2c3e5f21d126f42c96d1ad1ae3"
SCHEMA = json.loads(SCHEMA_PATH.read_text())

#: Ops/meta tools return no upstream data and are outside the v1.2 provenance rule.
META_TOOLS = {"get_server_capabilities", "get_diagnostics"}
DATA_CALLS: list[tuple[str, dict[str, Any]]] = [
    ("search_approvals", {"gene": "BRAF"}),
    ("search_approvals", {"gene": "BRAF", "response_mode": "full"}),
    ("search_approvals", {"gene": "KRAS", "limit": 0}),
    ("get_indication", {"indication_id": "ind:fda:tafinlar:4"}),
    ("list_biomarkers", {"gene": "EGFR"}),
]


def test_vendored_schema_is_the_pinned_release() -> None:
    assert hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest() == SCHEMA_SHA256


def test_every_data_tool_is_covered() -> None:
    assert {name for name, _ in DATA_CALLS} == set(TOOLS) - META_TOOLS


@pytest.mark.parametrize(("tool", "arguments"), DATA_CALLS)
async def test_data_tool_result_validates(
    facade: Any, call_tool: Any, tool: str, arguments: dict[str, Any]
) -> None:
    out = await call_tool(facade, tool, arguments)
    assert out["success"] is True
    jsonschema.validate(out, SCHEMA)
    meta = out["_meta"]
    assert meta["source"] == "moalmanac" and meta["data_version"] == snapshot.data_version()
    # a snapshot reports the time it was downloaded, not the time of the call
    assert meta["retrieved_at"] == snapshot.provenance()["retrieved_at"]
    assert out["data_version"] == meta["data_version"]  # deprecated top-level copy


async def test_error_result_validates(facade: Any, call_tool: Any) -> None:
    out = await call_tool(facade, "get_indication", {"indication_id": "ind:fda:nope:0"})
    assert out["success"] is False
    jsonschema.validate(out, SCHEMA)
