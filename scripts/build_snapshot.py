"""Build the bundled MOAlmanac snapshot (CC BY 4.0) from a pinned moalmanac-db release.

Source: vanallenlab/moalmanac-db ``referenced/*.json`` at the release tag ``TAG`` (commit
``COMMIT``), each file sha256-recorded. Only **Active** statements are kept (one row per
statement: one agency, one label version). The schema guard fails the build loudly when a
table or field this server reads is missing (2.0 was a full rebuild; the next one may be too).
Upstream data are not corrected here; known defects are documented in the README.

    uv run python scripts/build_snapshot.py                 # fetch the pinned tag from GitHub
    uv run python scripts/build_snapshot.py --source DIR    # a local checkout's referenced/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

TAG = "v.2026-11-05"
COMMIT = "719ba8a5fa4c85a0ab599dc0748ea1eaec024af9"
DOI = "10.5281/zenodo.23986188"
REPO = "vanallenlab/moalmanac-db"
OUT = Path(__file__).parents[1] / "moalmanac_link" / "data"
SCHEMA_VERSION = 1

#: Every table and field this build reads. A missing one aborts the build (schema guard).
REQUIRED: dict[str, set[str]] = {
    "about": {"release", "last_updated", "license"},
    "agents": {"id", "name"},
    "biomarker_criteria": {"id", "subject", "present"},
    "biomarkers": {"id", "name", "biomarker_type", "genes", "extensions"},
    "contributions": {"id", "agent_id", "description", "date"},
    "diseases": {"id", "name", "primary_coding_id", "mappings"},
    "documents": {
        "id", "agent_id", "name", "company", "drug_name_brand", "drug_name_generic",
        "publication_date", "regulatory_identifier", "status", "urls",
    },
    "genes": {"id", "name", "primary_coding_id", "mappings"},
    "indications": {
        "id", "description", "statement_description", "status", "contributions",
        "reportedIn", "raw_biomarkers", "raw_cancer_types", "raw_therapeutics", "superseded_by",
    },
    "mappings": {"id", "primary_coding_id", "coding_id"},
    "propositions": {
        "id", "predicate", "biomarker_criteria", "conditionQualifier_id", "therapy_id",
        "therapy_group_id",
    },
    "statements": {
        "id", "proposition_id", "indication_id", "reportedIn", "contributions", "status",
        "direction", "strength_id",
    },
    "strengths": {"id", "name"},
    "therapies": {"id", "name"},
    "therapy_groups": {"id", "membershipOperator", "therapies"},
    "urls": {"id", "url"},
}  # fmt: skip

#: Protein-expression markers -> the HGNC symbol of the gene product (alias expansion, so a
#: gene=ERBB2 query also finds "HER2-positive" rows, which upstream links to no gene).
MARKER_GENES = {
    "Human epidermal growth factor receptor 2 (HER2)": "ERBB2",
    "PD-L1": "CD274",
    "Estrogen receptor (ER)": "ESR1",
    "Progesterone receptor (PR)": "PGR",
    "EGFR": "EGFR",
    "c-Met": "MET",
    "CD117": "KIT",
    "PTEN": "PTEN",
    "CCND1": "CCND1",
    "CLDN18.2": "CLDN18",
    "FOLR1": "FOLR1",
    "CD19": "CD19",
    "CD20": "MS4A1",
    "CD22": "CD22",
    "CD30": "TNFRSF8",
    "CD33": "CD33",
}


class SchemaError(SystemExit):
    """The upstream release no longer has a table or field this server depends on."""


def check_schema(tables: dict[str, Any]) -> None:
    """Fail loudly (listing every gap) when an expected table or field is missing."""
    gaps: list[str] = []
    for name, fields in REQUIRED.items():
        table = tables.get(name)
        rows = [table] if isinstance(table, dict) else table
        if not rows:
            gaps.append(f"{name}: table missing or empty")
            continue
        for row in rows:
            missing = sorted(fields - set(row))
            if missing:
                gaps.append(f"{name}[{row.get('id', '?')}]: missing {', '.join(missing)}")
                break
    if gaps:
        raise SchemaError("moalmanac-db schema changed:\n  " + "\n  ".join(gaps))


def _code(coding_id: str) -> str:
    """``coding:ncit:C2926`` -> ``ncit:C2926``."""
    return coding_id.removeprefix("coding:")


def _agency(agent_id: str) -> str:
    return agent_id.rsplit(":", 1)[-1]


def derive(tables: dict[str, Any]) -> dict[str, Any]:
    """The compact, query-ready snapshot (approvals, indications, biomarkers, genes)."""
    check_schema(tables)
    by = {k: {r["id"]: r for r in v} for k, v in tables.items() if isinstance(v, list)}
    maps = by["mappings"]
    urls = {k: v["url"] for k, v in by["urls"].items()}

    genes: dict[str, dict[str, str]] = {}
    gene_symbol: dict[str, str] = {}
    for gid, g in by["genes"].items():
        ids = {"hgnc": "HGNC:" + _code(g["primary_coding_id"]).split(":", 1)[1]}
        for mid in g["mappings"]:
            scheme, _, value = _code(maps[mid]["coding_id"]).partition(":")
            if scheme == "ensembl":
                ids["ensembl"] = value.upper()
            elif scheme == "ncbi":
                ids["ncbi"] = value
        genes[g["name"]] = ids
        gene_symbol[gid] = g["name"]

    def marker_genes(b: dict[str, Any]) -> list[str]:
        ext = {e["name"]: e["value"] for e in b["extensions"]}
        symbol = MARKER_GENES.get(str(ext.get("marker")))
        # A "Negative" marker is the absence of the product: not an approval *for* that gene.
        return [symbol] if symbol and ext.get("value") != "Negative" else []

    biomarkers: dict[str, dict[str, Any]] = {}
    for bid, b in by["biomarkers"].items():
        linked = [gene_symbol[g] for g in b["genes"]] + marker_genes(b)
        biomarkers[bid] = {
            "name": b["name"],
            "type": b["biomarker_type"],
            "genes": sorted(set(linked)),
            "approvals": 0,
            "approvals_when_absent": 0,
        }

    def disease(did: str) -> dict[str, Any]:
        d = by["diseases"][did]
        oncotree = [_code(maps[m]["coding_id"]) for m in d["mappings"]]
        return {
            "name": d["name"],
            "ncit": _code(d["primary_coding_id"]),
            "oncotree": [c.split(":", 1)[1] for c in oncotree if c.startswith("oncotree:")],
        }

    def document(did: str) -> dict[str, Any]:
        d = by["documents"][did]
        label = [urls[u] for u in d["urls"] if ":label" in u]
        return {
            "document_id": did,
            "name": d["name"],
            "company": d["company"],
            "brand": d["drug_name_brand"],
            "generic": d["drug_name_generic"],
            "version_date": d["publication_date"],
            "regulatory_id": d["regulatory_identifier"],
            "status": d["status"],
            "url": label[0] if label else (urls[d["urls"][0]] if d["urls"] else None),
        }

    approvals: list[dict[str, Any]] = []
    for s in by["statements"].values():
        if s["status"] != "Active":
            continue
        prop = by["propositions"][s["proposition_id"]]
        ind = by["indications"][s["indication_id"]]
        docs = [document(d) for d in s["reportedIn"]]
        label = next((d for d in docs if d["status"] == "Active"), docs[0])
        agency = _agency(by["documents"][label["document_id"]]["agent_id"])
        if prop["therapy_id"]:
            therapy_ids, operator = [prop["therapy_id"]], None
        else:
            group = by["therapy_groups"][prop["therapy_group_id"]]
            therapy_ids, operator = group["therapies"], group["membershipOperator"]
        criteria = [by["biomarker_criteria"][c] for c in prop["biomarker_criteria"]]
        markers = []
        for c in criteria:
            # a criterion can require absence ("NOT KIT p.D816V"): counted apart, as the rows say
            biomarkers[c["subject"]]["approvals" if c["present"] else "approvals_when_absent"] += 1
            markers.append({**biomarkers[c["subject"]], "present": c["present"]})
        dates = [
            by["contributions"][c]["date"]
            for c in s["contributions"]
            if _agency(by["contributions"][c]["agent_id"]) == agency
        ]
        approvals.append(
            {
                "statement_id": s["id"],
                "indication_id": ind["id"],
                "agency": agency,
                "status": ind["status"],
                "first_agency_date": min(dates) if dates else None,
                "biomarkers": [
                    (m["name"] if m["present"] else f"NOT {m['name']}") for m in markers
                ],
                "biomarker_types": sorted({m["type"] for m in markers}),
                "genes": sorted({g for m in markers if m["present"] for g in m["genes"]}),
                "disease": disease(prop["conditionQualifier_id"]),
                "therapies": [by["therapies"][t]["name"] for t in therapy_ids],
                "therapy_operator": operator,
                "predicate": prop["predicate"],
                "strength": by["strengths"][s["strength_id"]]["name"],
                "direction": s["direction"],
                "label": {k: label[k] for k in ("document_id", "name", "brand", "generic",
                                                 "version_date", "regulatory_id", "url")},
            }
        )  # fmt: skip
    approvals.sort(key=lambda r: (r["disease"]["name"], r["therapies"], r["agency"]))

    indications: dict[str, dict[str, Any]] = {}
    for iid, ind in by["indications"].items():
        indications[iid] = {
            "indication_id": iid,
            "status": ind["status"],
            "description": ind["description"],
            "statement_description": ind["statement_description"],
            "raw_biomarkers": ind["raw_biomarkers"],
            "raw_cancer_types": ind["raw_cancer_types"],
            "raw_therapeutics": ind["raw_therapeutics"],
            "reimbursement_scheme": ind.get("reimbursement_scheme"),
            "reimbursement_comment": ind.get("reimbursement_comment"),
            "superseded_by": ind["superseded_by"],
            "contributions": sorted(
                (
                    {
                        "date": by["contributions"][c]["date"],
                        "agent": by["agents"][by["contributions"][c]["agent_id"]]["name"],
                        "description": by["contributions"][c]["description"],
                    }
                    for c in ind["contributions"]
                ),
                key=lambda c: c["date"],
            ),
            "documents": [document(d) for d in ind["reportedIn"]],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "approvals": approvals,
        "indications": indications,
        "biomarkers": sorted(biomarkers.values(), key=lambda b: (b["type"], b["name"])),
        "genes": genes,
        "agencies": {_agency(a["id"]): a["name"] for a in tables["agents"]
                     if a["id"].startswith("agent:org:")},
    }  # fmt: skip


def _fetch(name: str, source: Path | None) -> bytes:
    if source is not None:
        return (source / f"{name}.json").read_bytes()
    url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/referenced/{name}.json"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return bytes(resp.read())


def main(argv: list[str] | None = None) -> int:
    """Fetch, verify, derive and write the snapshot + provenance."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, help="local referenced/ directory at COMMIT")
    args = parser.parse_args(argv)
    raw = {name: _fetch(name, args.source) for name in REQUIRED}
    tables = {name: json.loads(blob) for name, blob in raw.items()}
    snapshot = derive(tables)
    blob = json.dumps(snapshot, separators=(",", ":"), sort_keys=True).encode()
    OUT.mkdir(exist_ok=True)
    (OUT / "moalmanac_snapshot.json").write_bytes(blob)
    provenance = {
        "dataset": "Molecular Oncology Almanac (MOAlmanac) database, referenced/ tables",
        "data_version": TAG,
        "release": tables["about"]["release"],
        "upstream_last_updated": tables["about"]["last_updated"],
        "source_repo": REPO,
        "source_commit": COMMIT,
        "doi": DOI,
        "license": "CC-BY-4.0 (https://creativecommons.org/licenses/by/4.0/)",
        "attribution": "Molecular Oncology Almanac, Van Allen lab, Dana-Farber Cancer Institute "
        "/ Broad Institute (https://moalmanac.org)",
        "citation": "Reardon B et al. Integrating molecular profiles into clinical frameworks "
        "through the Molecular Oncology Almanac to prospectively guide precision oncology. "
        "Nat Cancer 2021. PMID 35121878. doi:10.1038/s43018-021-00243-3",
        "source_sha256": {f"referenced/{n}.json": hashlib.sha256(b).hexdigest()
                          for n, b in sorted(raw.items())},
        "derived_file": "moalmanac_snapshot.json",
        "derived_sha256": hashlib.sha256(blob).hexdigest(),
        "counts": {"approvals": len(snapshot["approvals"]),
                   "indications": len(snapshot["indications"]),
                   "biomarkers": len(snapshot["biomarkers"])},
    }  # fmt: skip
    (OUT / "moalmanac_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"wrote {len(blob):,} bytes; {provenance['counts']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
