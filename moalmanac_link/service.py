"""MOAlmanac data plane: validate filters, query the bundled snapshot, shape honest payloads.

Returns plain dicts and raises typed :mod:`moalmanac_link.exceptions` errors; the MCP envelope
owns ``success``/``_meta``. Every filter value must match the release's vocabulary (else
``not_found`` naming the field: never a silently empty answer). An empty combination says
"No MOAlmanac approval found", never "not approved": MOAlmanac is a curated subset of labels
and can lag behind the agencies.
"""

from __future__ import annotations

import re
from typing import Any

from moalmanac_link import snapshot
from moalmanac_link.exceptions import InvalidInputError, NotFoundError
from moalmanac_link.mcp.next_commands import cmd
from moalmanac_link.shaping import fence, page_block

AGENCIES = ("fda", "ema", "hc", "hse", "hpra")
GENE_FORMS = [
    "HGNC symbol (ERBB2) or protein alias (HER2, PD-L1)",
    "HGNC ID (HGNC:3430)",
    "Ensembl gene ID (ENSG00000141736)",
    "NCBI Gene ID (2064 or NCBIGene:2064)",
]
#: Protein names agents use for a gene product; upstream keys some biomarkers on them.
GENE_ALIASES = {"HER2": "ERBB2", "PD-L1": "CD274", "PDL1": "CD274"}
_HGNC = re.compile(r"^HGNC:\d{1,6}$", re.I)
_ENSG = re.compile(r"^(ENSG\d{11})(?:\.\d+)?$", re.I)
_NCBI = re.compile(r"^(?:NCBIGene:)?(\d{1,9})$", re.I)
_SYMBOL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,29}$")
_INDICATION = re.compile(r"^ind:[a-z]{2,4}:[A-Za-z0-9_.\-]{1,60}:[A-Za-z0-9_]{1,10}$")
_MINIMAL = ("statement_id", "indication_id", "agency", "status", "biomarkers", "therapies")
_STANDARD_ONLY = ("biomarker_types", "predicate", "strength", "direction")
_NO_APPROVAL = (
    "No MOAlmanac approval found for these filters in release {dv}. This is not evidence that "
    "no approval exists: MOAlmanac curates a subset of FDA, EMA, Health Canada, HSE and HPRA "
    "labels and can lag behind them."
)


def _norm(text: str) -> str:
    """Lowercase, drop HGVS ``p.``, collapse punctuation: ``BRAF p.V600E`` -> ``braf v600e``."""
    return " ".join(re.sub(r"[^a-z0-9.+<>=%*]+", " ", text.lower().replace("p.", "")).split())


def _matches(query: str, *texts: str) -> bool:
    """Every query token occurs in one of the texts (``V600`` also matches ``V600E``)."""
    tokens = _norm(query).split()
    return any(all(t in _norm(text) for t in tokens) for text in texts) if tokens else False


def _unknown(field: str, what: str, step: dict[str, Any]) -> NotFoundError:
    return NotFoundError(
        f"No MOAlmanac approval found: the `{field}` value matches no {what} in MOAlmanac "
        f"release {snapshot.data_version()}.",
        field=field,
        next_commands=[step],
    )


def source() -> dict[str, Any]:
    """The CC BY 4.0 attribution every payload carries."""
    prov = snapshot.provenance()
    return {
        "name": "Molecular Oncology Almanac (MOAlmanac)",
        "license": "CC-BY-4.0",
        "attribution": prov["attribution"],
        "doi": prov["doi"],
    }


class MoaService:
    """All MOAlmanac queries over the bundled snapshot; one instance per process."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        """Bind the verified snapshot (loaded eagerly so a bad file fails startup)."""
        self.data = data if data is not None else snapshot.load()
        self.genes: dict[str, str] = {}
        for symbol, ids in self.data["genes"].items():
            for key in (symbol, ids.get("hgnc"), ids.get("ensembl"), ids.get("ncbi")):
                if key:
                    self.genes[key.upper()] = symbol
        for row in self.data["approvals"]:
            for symbol in row["genes"]:
                self.genes.setdefault(symbol.upper(), symbol)
        self.genes.update({k: v for k, v in GENE_ALIASES.items() if v.upper() in self.genes})

    def _stamp(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["data_version"] = snapshot.data_version()
        payload["source"] = source()
        return payload

    def resolve_gene(self, gene: str) -> str:
        """Any accepted gene form -> the HGNC symbol MOAlmanac uses."""
        raw = gene.strip()
        ensg, ncbi = _ENSG.match(raw), _NCBI.match(raw)
        if ensg:
            key = ensg.group(1)
        elif ncbi:
            key = ncbi.group(1)
        elif _HGNC.match(raw) or _SYMBOL.match(raw):
            key = raw
        else:
            raise InvalidInputError(
                "`gene` must be one gene: a symbol, HGNC ID, Ensembl gene ID or NCBI Gene ID. "
                "Put a variant such as V600E in `biomarker`.",
                field="gene",
                allowed_values=GENE_FORMS,
                next_commands=[cmd("list_biomarkers")],
            )
        symbol = self.genes.get(key.upper())
        if symbol is None:
            raise _unknown("gene", "gene", cmd("list_biomarkers"))
        return symbol

    def _rows(
        self,
        gene: str | None,
        biomarker: str | None,
        disease: str | None,
        therapy: str | None,
        agency: str | None,
    ) -> list[dict[str, Any]]:
        if agency is not None and agency not in AGENCIES:
            raise InvalidInputError(
                "`agency` must be one of fda, ema, hc, hse, hpra.",
                field="agency",
                allowed_values=list(AGENCIES),
            )
        rows: list[dict[str, Any]] = self.data["approvals"]
        if gene is not None:
            rows = [r for r in rows if gene in r["genes"]]
        if biomarker is not None:
            if not any(_matches(biomarker, b["name"]) for b in self.data["biomarkers"]):
                raise _unknown("biomarker", "biomarker", cmd("list_biomarkers"))
            rows = [
                r
                for r in rows
                if _matches(biomarker, *(b for b in r["biomarkers"] if not b.startswith("NOT ")))
            ]
        if disease is not None:
            if not any(self._disease_hit(disease, r) for r in self.data["approvals"]):
                raise _unknown(
                    "disease", "disease name, OncoTree or NCIt code", cmd("search_approvals")
                )
            rows = [r for r in rows if self._disease_hit(disease, r)]
        if therapy is not None:
            if not any(self._therapy_hit(therapy, r) for r in self.data["approvals"]):
                raise _unknown("therapy", "therapy or brand name", cmd("search_approvals"))
            rows = [r for r in rows if self._therapy_hit(therapy, r)]
        if agency is not None:
            rows = [r for r in rows if r["agency"] == agency]
        return rows

    @staticmethod
    def _disease_hit(query: str, row: dict[str, Any]) -> bool:
        d = row["disease"]
        code = query.strip()
        if code.upper() in d["oncotree"] or code.lower() in (
            d["ncit"].lower(),
            d["ncit"][5:].lower(),
        ):
            return True
        return _matches(query, d["name"])

    @staticmethod
    def _therapy_hit(query: str, row: dict[str, Any]) -> bool:
        label = row["label"]
        return _matches(query, *row["therapies"], label["brand"] or "", label["generic"] or "")

    def _shape(self, row: dict[str, Any], mode: str) -> dict[str, Any]:
        if mode == "minimal":
            out = {k: row[k] for k in _MINIMAL}
            out["disease"] = row["disease"]["name"]
            out["label"] = {k: row["label"][k] for k in ("document_id", "version_date")}
            return out
        out = {k: v for k, v in row.items() if k not in _STANDARD_ONLY}
        out["label"] = {k: v for k, v in row["label"].items() if k != "url"}
        if mode in ("standard", "full"):
            out.update({k: row[k] for k in _STANDARD_ONLY})
            out["label"] = dict(row["label"])
        if mode == "full":
            ind = self.data["indications"][row["indication_id"]]
            out["indication"] = fence(ind["description"], row["indication_id"])
        return out

    async def search_approvals(
        self,
        gene: str | None,
        biomarker: str | None,
        disease: str | None,
        therapy: str | None,
        agency: str | None,
        limit: int,
        offset: int,
        response_mode: str,
    ) -> dict[str, Any]:
        """Regulatory approvals matching every given filter, one row per agency statement."""
        symbol = self.resolve_gene(gene) if gene is not None else None
        rows = self._rows(symbol, biomarker, disease, therapy, agency)
        page = rows[offset : offset + limit]
        query = {
            k: v
            for k, v in {
                "gene": symbol,
                "biomarker": biomarker,
                "disease": disease,
                "therapy": therapy,
                "agency": agency,
            }.items()
            if v is not None
        }
        payload: dict[str, Any] = {"query": query}
        if gene is not None and gene.strip() != symbol:
            payload["resolved_from"] = gene.strip()
        payload["approvals"] = [self._shape(r, response_mode) for r in page]
        payload.update(page_block(total=len(rows), returned=len(page), limit=limit, offset=offset))
        payload["response_mode"] = response_mode
        if not rows:
            payload["message"] = _NO_APPROVAL.format(dv=snapshot.data_version())
        return self._stamp(payload)

    async def get_indication(self, indication_id: str) -> dict[str, Any]:
        """One indication: fenced label text, history, label documents and its approvals."""
        key = indication_id.strip()
        if not _INDICATION.match(key):
            raise InvalidInputError(
                "`indication_id` must look like ind:fda:lumakras:0 (from search_approvals).",
                field="indication_id",
                allowed_values=["ind:<agency>:<product>:<n>"],
                next_commands=[cmd("search_approvals")],
            )
        ind = self.data["indications"].get(key)
        if ind is None:
            raise NotFoundError(
                "No MOAlmanac indication has this `indication_id`; find one with search_approvals.",
                field="indication_id",
                next_commands=[cmd("search_approvals")],
            )
        prose = (
            "description",
            "statement_description",
            "raw_biomarkers",
            "raw_cancer_types",
            "raw_therapeutics",
            "reimbursement_comment",
        )
        out = {k: (fence(v, key) if k in prose else v) for k, v in ind.items()}
        out["contributions"] = [
            {**c, "description": fence(c["description"], key)} for c in ind["contributions"]
        ]
        rows = [r for r in self.data["approvals"] if r["indication_id"] == key]
        return self._stamp(
            {"indication": out, "approvals": [self._shape(r, "compact") for r in rows]}
        )

    async def list_biomarkers(
        self, gene: str | None, biomarker_type: str | None, limit: int, offset: int
    ) -> dict[str, Any]:
        """MOAlmanac's biomarker vocabulary (name, type, genes, active approval count)."""
        symbol = self.resolve_gene(gene) if gene is not None else None
        rows = [
            b
            for b in self.data["biomarkers"]
            if (symbol is None or symbol in b["genes"])
            and (biomarker_type is None or b["type"] == biomarker_type)
        ]
        rows.sort(key=lambda b: (-b["approvals"], b["name"]))
        page = rows[offset : offset + limit]
        payload: dict[str, Any] = {"query": {"gene": symbol, "biomarker_type": biomarker_type}}
        payload["biomarkers"] = page
        payload.update(page_block(total=len(rows), returned=len(page), limit=limit, offset=offset))
        return self._stamp(payload)
