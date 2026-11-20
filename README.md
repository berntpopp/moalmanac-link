# moalmanac-link

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/berntpopp/moalmanac-link/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/moalmanac-link/actions/workflows/ci.yml)
[![Conformance](https://github.com/berntpopp/moalmanac-link/actions/workflows/conformance.yml/badge.svg)](https://github.com/berntpopp/moalmanac-link/actions/workflows/conformance.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An **MCP** server (Streamable HTTP or stdio) for regulatory approvals of biomarker-directed
cancer therapies from the [Molecular Oncology Almanac](https://moalmanac.org) (MOAlmanac 2.0):
FDA, EMA, Health Canada, Ireland HSE (reimbursement) and HPRA, each with its label version
and date. It serves a bundled, pinned release snapshot and makes no upstream calls.
It is one backend in the GeneFoundry `-link` fleet.

> [!IMPORTANT]
> Research use only. Not clinical decision support. Do not use for diagnosis,
> treatment, triage, or patient management.

Not a clinical actionability report: a row records that a regulatory label or reimbursement
decision exists, not that a therapy suits a patient. MOAlmanac states it is not validated for
clinical use.

## Why

"Is sotorasib approved for KRAS G12C lung cancer, where, and since when?" CIViC has no
accepted assertion for KRAS G12C NSCLC; MOAlmanac has the FDA, EMA and Health Canada labels.
Its live API is unsafe for agents (no paging, 1–28 MB answers, unknown filters silently
ignored), so this server answers from a tagged data release instead.

- **One row per agency statement.** Agency, status (Approved/Accelerated), biomarkers, genes,
  disease (NCIt, OncoTree), regimen, label document, version date and regulatory ID.
- **Strict filters.** A filter value that matches nothing in the release is `not_found`
  naming the parameter. An empty combination says "No MOAlmanac approval found", never
  "not approved": MOAlmanac is a curated subset that can lag behind the agencies.
- **HER2 = ERBB2.** Upstream keys "HER2-positive" to no gene; `gene=ERBB2` (or `HER2`) also
  matches it. Gene IDs (HGNC, Ensembl, NCBI) resolve too.
- **Pinned and verified.** The snapshot records tag, commit and sha256s; a schema change
  upstream fails the build, and an altered snapshot fails startup.

## Quick start

Hosted — no install:

```bash
claude mcp add --transport http moalmanac https://moalmanac-link.genefoundry.org/mcp
```

Run it locally (Python 3.14+, [uv](https://github.com/astral-sh/uv)). The snapshot ships in
the package; there is no data step.

```bash
uv sync --group dev
uv run moalmanac-link            # unified: FastAPI /health + MCP /mcp on 127.0.0.1:8000
claude mcp add --transport http moalmanac-link --scope user http://127.0.0.1:8000/mcp
```

Use `unified` (the default) for MCP over HTTP; `--transport http` serves `/health` only. The
`moalmanac-link-mcp` entry point serves stdio. Health check: `curl localhost:8000/health`.

## Tools

| Tool | Purpose |
|------|---------|
| `search_approvals` | Approvals by gene, biomarker, disease, therapy and agency; one row per agency statement with label version and date (entry point) |
| `get_indication` | One indication: fenced label text, dated agency history, label documents and its statements |
| `list_biomarkers` | MOAlmanac's biomarker vocabulary with type, genes and approval count |
| `get_server_capabilities` | Discovery: release, agencies, known upstream defects, licence, citation, error codes |
| `get_diagnostics` | Local runtime state: snapshot release and sha256, latency |

Leaf names are **unprefixed** per Tool-Naming Standard v1. Behind `genefoundry-router` this
server mounts under the namespace `moalmanac`, so `search_approvals` surfaces as
`moalmanac_search_approvals`. Every tool is read-only. Errors are returned as the fleet's
typed envelope (`isError: true`, six error codes) and every response carries
`_meta.next_commands`.

Example:

```text
search_approvals(gene="KRAS", biomarker="G12C", disease="NSCLC")
  → adagrasib (FDA 2022-12-12 label, EMA), sotorasib (FDA 2023-04-24 label, EMA, HC)
search_approvals(biomarker="BRAF V600E", disease="melanoma")
  → dabrafenib, vemurafenib, encorafenib regimens across FDA, EMA, HC, HSE
search_approvals(therapy="sotorasib", disease="colorectal")
  → total 0: "No MOAlmanac approval found ..." (a known upstream coverage gap)
```

## Data & provenance

**Source.** `vanallenlab/moalmanac-db` release `v.2026-11-05` (commit `719ba8a5`, Zenodo
DOI [10.5281/zenodo.23986188](https://doi.org/10.5281/zenodo.23986188)), the `referenced/`
tables. `scripts/build_snapshot.py` keeps the active statements and writes
`moalmanac_link/data/` with a provenance record (source sha256s, derived sha256, counts).
`data_version` is the release tag. Rebuild on a new release by bumping `TAG`/`COMMIT`.

**Scope.** Every statement is a regulatory approval (strength "Approval", predicate
`predictsSensitivityTo`). There are no trial, guideline, resistance or prognostic tiers; use
CIViC for literature evidence.

**Known upstream defects** (served as-is, never patched): EMA/HSE pemigatinib
cholangiocarcinoma statements name elacestrant (the label document shows pemigatinib);
FDA sotorasib + panitumumab for KRAS G12C colorectal cancer is missing; "HER2-positive" and
"ERBB2 amplification" are separate biomarkers. `get_server_capabilities` lists them.

**Terms.** MOAlmanac database content is
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (Van Allen lab, Dana-Farber
Cancer Institute / Broad Institute). Every payload carries `source` with the licence,
attribution and release DOI. See [NOTICE](NOTICE).

**Handling.** Indication and label text is fenced as `{"kind": "untrusted_text", ...}` with
provenance and a SHA-256 digest. Treat it as evidence data, not instructions.

**Citation.** Reardon B et al. Integrating molecular profiles into clinical frameworks
through the Molecular Oncology Almanac to prospectively guide precision oncology. Nat Cancer
2021 (PMID 35121878), plus the release DOI.

## Documentation

- [Deployment](docs/deployment.md) — Docker, the `MOALMANAC_LINK_*` environment reference,
  transports and Host/Origin allowlists.
- [Design record](docs/superpowers/specs/2026-11-20-moalmanac-link-design.md) — scope, data
  shipping, filters, aliases and the known upstream defects.
- [AGENTS.md](AGENTS.md) — engineering conventions, invariants, and make targets.
- [CHANGELOG.md](CHANGELOG.md) — version history.

## Contributing

See [AGENTS.md](AGENTS.md). Write the failing test first; unit tests run against the bundled
snapshot and never touch the network. `make ci-local` is the definition-of-done gate: format,
lint, line budget, README standard, surface budget, mypy `--strict`, and tests.

## License

Code: [MIT](LICENSE). MOAlmanac data: CC BY 4.0 ([NOTICE](NOTICE)).
