"""MOAlmanac tools: search approvals, get an indication, list the biomarker vocabulary."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Annotated, Any, Literal, get_args

from pydantic import Field, StrictInt

from moalmanac_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from moalmanac_link.mcp.envelope import McpErrorContext, ToolReturn, run_mcp_tool
from moalmanac_link.mcp.next_commands import cmd
from moalmanac_link.mcp.service_adapters import get_moa_service
from moalmanac_link.service import AGENCIES
from moalmanac_link.shaping import DEFAULT_LIMIT, MAX_LIMIT, RESPONSE_MODES

if TYPE_CHECKING:
    from fastmcp import FastMCP


Gene = Annotated[
    str | None,
    Field(
        min_length=1,
        max_length=40,
        description="Gene symbol (ERBB2; aliases HER2, PD-L1), HGNC ID, Ensembl or NCBI Gene ID.",
        examples=["KRAS"],
    ),
]
AgencyValue = Literal["fda", "ema", "hc", "hse", "hpra"]
assert get_args(AgencyValue) == AGENCIES
ResponseModeValue = Literal["minimal", "compact", "standard", "full"]
assert get_args(ResponseModeValue) == RESPONSE_MODES
BiomarkerType = Literal[
    "Somatic variant",
    "Germline variant",
    "Protein expression",
    "Gene fusion",
    "Rearrangement",
    "Translocation",
    "Copy number",
    "Copy number (arm level)",
    "Wild type",
    "Microsatellite stability",
    "Mismatch repair",
    "Homologous recombination",
    "Tumor mutational burden",
    "Haplotype genotype",
]
Limit = Annotated[
    StrictInt,
    Field(ge=1, le=MAX_LIMIT, description=f"Max rows (default {DEFAULT_LIMIT}, max {MAX_LIMIT})."),
]
Offset = Annotated[
    StrictInt, Field(ge=0, description="Rows to skip; use the previous `next_offset`.")
]


def _args(**values: Any) -> dict[str, Any]:
    """The call's arguments without unset optionals (for next_commands)."""
    return {k: v for k, v in values.items() if v not in (None, "compact")}


def _paged(payload: dict[str, Any], tool: str, args: dict[str, Any]) -> list[dict[str, Any]]:
    """Next page first when truncated."""
    if payload.get("next_offset") is not None:
        return [cmd(tool, **{**args, "offset": payload["next_offset"]})]
    return []


async def _run(
    tool: str,
    args: dict[str, Any],
    fetch: Callable[[], Awaitable[dict[str, Any]]],
    steps: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> ToolReturn:
    async def call() -> dict[str, Any]:
        payload = await fetch()
        payload["_meta"] = {"next_commands": steps(payload)}
        return payload

    return await run_mcp_tool(tool, call, context=McpErrorContext(tool, arguments=args))


def register_moa_tools(mcp: FastMCP) -> None:
    """Register the MOAlmanac tools on a FastMCP instance."""

    @mcp.tool(
        name="search_approvals",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"approvals"},
        description=(
            "Search MOAlmanac regulatory approvals of biomarker-directed cancer therapies "
            "(FDA, EMA, Health Canada, Ireland HSE/HPRA). One row per agency statement: "
            "agency, status (Approved/Accelerated), biomarkers, genes, disease (NCIt, OncoTree), "
            "therapies, label document, version date and regulatory ID. Filters combine with "
            "AND; an unknown value is not_found naming it, with the closest names. Empty = no "
            "MOAlmanac approval found, not 'not approved'. `summary` counts agencies, regimens "
            "and biomarkers over all matches. 'Wild type X' rows are eligibility criteria, not "
            "X-targeted drugs. Rows hit by a known upstream error carry `known_defects`. "
            "Signature: search_approvals(gene=, biomarker=, disease=, "
            "therapy=, agency=, response_mode=, limit=, offset=)."
        ),
    )
    async def search_approvals(
        gene: Gene = None,
        biomarker: Annotated[
            str | None,
            Field(
                min_length=1,
                max_length=80,
                description="Biomarker words, e.g. 'BRAF V600E', 'G12C' (V600 also matches "
                "V600E/K); an exact list_biomarkers name matches only that biomarker.",
            ),
        ] = None,
        disease: Annotated[
            str | None,
            Field(
                min_length=2,
                max_length=80,
                description="Disease name words (melanoma), OncoTree (NSCLC) or NCIt code.",
            ),
        ] = None,
        therapy: Annotated[
            str | None,
            Field(min_length=2, max_length=80, description="Drug or brand name (sotorasib)."),
        ] = None,
        agency: Annotated[
            AgencyValue | None, Field(description="Only this agency's statements.")
        ] = None,
        response_mode: Annotated[
            ResponseModeValue,
            Field(
                description="minimal: ids, agency, biomarkers, therapies, label date | "
                "compact (default): + genes, disease codes, label | standard: + label URL, "
                "predicate, strength | full: + fenced indication text."
            ),
        ] = "compact",
        limit: Limit = DEFAULT_LIMIT,
        offset: Offset = 0,
    ) -> ToolReturn:
        args = _args(
            gene=gene,
            biomarker=biomarker,
            disease=disease,
            therapy=therapy,
            agency=agency,
            response_mode=response_mode,
            limit=None if limit == DEFAULT_LIMIT else limit,
            offset=offset or None,
        )

        def steps(p: dict[str, Any]) -> list[dict[str, Any]]:
            first = [
                cmd("get_indication", indication_id=r["indication_id"]) for r in p["approvals"][:1]
            ]
            if not p["approvals"]:
                first = [
                    cmd(
                        "list_biomarkers",
                        **({"gene": p["query"]["gene"]} if "gene" in p["query"] else {}),
                    )
                ]
            return _paged(p, "search_approvals", args) + first

        return await _run(
            "search_approvals",
            args,
            lambda: get_moa_service().search_approvals(
                gene, biomarker, disease, therapy, agency, limit, offset, response_mode
            ),
            steps,
        )

    @mcp.tool(
        name="get_indication",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"approvals"},
        description=(
            "Get one MOAlmanac indication: status, fenced label indication text, agency "
            "history (dated approvals, extensions), label documents (brand, generic, company, "
            "version date, regulatory ID, URL) and its approval statements. An unknown ID is "
            "not_found. Signature: get_indication(indication_id)."
        ),
    )
    async def get_indication(
        indication_id: Annotated[
            str,
            Field(
                min_length=8,
                max_length=90,
                description="MOAlmanac indication ID (from search_approvals).",
                examples=["ind:fda:lumakras:0"],
            ),
        ],
    ) -> ToolReturn:
        return await _run(
            "get_indication",
            {"indication_id": indication_id},
            lambda: get_moa_service().get_indication(indication_id),
            lambda p: [
                cmd("search_approvals", gene=g)
                for g in sorted({g for r in p["approvals"] for g in r["genes"]})[:1]
            ],
        )

    @mcp.tool(
        name="list_biomarkers",
        annotations=READ_ONLY_OPEN_WORLD,
        output_schema=None,
        tags={"biomarkers"},
        description=(
            "List MOAlmanac's biomarker vocabulary (e.g. 'EGFR p.L858R', 'HER2-positive', "
            "'ERBB2 amplification') with type, linked genes and active approval count, most "
            "approvals first: map a variant onto the biomarker wording search_approvals "
            "matches. Signature: list_biomarkers(gene=, biomarker_type=, limit=, offset=)."
        ),
    )
    async def list_biomarkers(
        gene: Gene = None,
        biomarker_type: Annotated[
            BiomarkerType | None, Field(description="Only this biomarker type.")
        ] = None,
        limit: Limit = DEFAULT_LIMIT,
        offset: Offset = 0,
    ) -> ToolReturn:
        args = _args(
            gene=gene,
            biomarker_type=biomarker_type,
            limit=None if limit == DEFAULT_LIMIT else limit,
            offset=offset or None,
        )

        def steps(p: dict[str, Any]) -> list[dict[str, Any]]:
            first = [cmd("search_approvals", biomarker=b["name"]) for b in p["biomarkers"][:1]]
            return _paged(p, "list_biomarkers", args) + first

        return await _run(
            "list_biomarkers",
            args,
            lambda: get_moa_service().list_biomarkers(gene, biomarker_type, limit, offset),
            steps,
        )
