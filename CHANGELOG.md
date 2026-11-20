# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-20

### Added

- `search_approvals(biomarker_type=)`: only rows with a biomarker of that type (of `gene`,
  if given), e.g. `Gene fusion` separates ALK-fusion approvals from "Wild type ALK" rows.
- `search_approvals(limit=0)` returns only `total` and `summary`; `summary` (first page)
  counts agencies, regimens, biomarkers and diseases over every match, with `distinct` totals
  and `known_defect_rows`.
- Rows and `get_indication` affected by a known upstream defect carry `known_defects`; the
  register adds the Lumakras status, Datroway disease, Lazcluze label and Tagrisso regimen
  defects and the HER2-negative gene gap.
- `not_found` for a gene, biomarker, disease or therapy names the closest vocabulary entries
  in `candidates` with ready retries; `get_indication` with a bare product name suggests its IDs;
  a wrong-case enum value (`agency="FDA"`) gets a corrected retry.
- Agent UX evaluation protocol, frozen tasks and runner (`docs/benchmarks/`, `scripts/agent_ux_*`).

### Fixed

- Generic disease words no longer narrow or fail a search: "breast cancer" was `not_found`
  and "ovarian cancer" matched 2 of 57 ovarian rows.
- An exact `list_biomarkers` name matches only that biomarker ("EGFR activating variants"
  no longer also returns "EGFR TKD activating variants").
- `therapy=` also matches the label name (the HSE pemigatinib regimen was unreachable).

## [0.1.0] - 2026-11-20

### Added

- Read-only MCP server over a bundled Molecular Oncology Almanac (MOAlmanac 2.0) release
  snapshot: regulatory approvals of biomarker-directed cancer therapies from FDA, EMA,
  Health Canada, Ireland HSE and HPRA (CC BY 4.0). No outbound requests at runtime.
- Tools: `search_approvals` (entry point), `get_indication`, `list_biomarkers`,
  `get_server_capabilities`, `get_diagnostics`.
- Strict filters: a gene, biomarker, disease or therapy value that matches nothing in the
  release is `not_found` naming the parameter; an empty combination says "No MOAlmanac
  approval found", never "not approved". HER2/PD-L1 aliases and HGNC/Ensembl/NCBI gene IDs
  resolve to the HGNC symbol.
- `scripts/build_snapshot.py` builds the snapshot from moalmanac-db `v.2026-11-05`
  (commit `719ba8a5`) with a schema guard; the server verifies the snapshot sha256 and
  schema at startup. Known upstream defects are documented and served as-is.
