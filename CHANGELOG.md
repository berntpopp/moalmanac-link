# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.4.0] - 2026-11-26

### Added

- Paged tools (`list_biomarkers`, `search_approvals`) report `_meta.pagination` with `total_count`, `has_more` and
  `next_cursor` (`null` where paging is by offset, which then also carries `next_offset`), as
  Response-Envelope Standard v1 §5 asks. The top-level paging fields are unchanged.

## [0.3.0] - 2026-11-26

### Added

- Response-Envelope Standard v1.2: every successful data result carries `_meta.source`,
  `_meta.data_version` (the MOAlmanac release tag) and `_meta.retrieved_at` (UTC time the
  bundled snapshot was downloaded from the upstream).
- `moalmanac_provenance.json` records `retrieved_at`; `scripts/build_snapshot.py` writes it. For
  the shipped snapshot the download time was not recorded, so it is the time the snapshot was
  last committed.
- Schema tests: every data tool result is validated against the vendored
  `envelope-v1.2.schema.json` (genefoundry-envelope v1.2.0, sha256-pinned).

### Changed

- **Breaking:** the primary payload key is now `results` (`search_approvals`,
  `list_biomarkers`) or `result` (`get_indication`), per Response-Envelope Standard v1 §1. It
  was `approvals`, `biomarkers` and `indication`. `get_indication` still lists its
  `approvals` beside `result`.
- Re-vendored `tests/conformance/behaviour.py` from genefoundry-router (v1.2 provenance check).

### Deprecated

- The top-level `data_version` of a data result. Read it from `_meta`; the top-level copy will
  be removed in the next minor release.

## [0.2.2] - 2026-11-21

### Fixed

- `search_approvals(biomarker="NOT <name>")` with `gene=` or `biomarker_type=` returned an
  empty success: those filters read the row's present biomarkers only, and a "NOT" row's
  required-absent biomarker is not one. They now also match the absent biomarker's own genes
  and type, so `gene="KIT", biomarker="NOT KIT p.D816V"` returns its 2 imatinib rows (#4).

## [0.2.1] - 2026-11-21

### Fixed

- `list_biomarkers` counted approvals that require a biomarker's *absence* as approvals for
  it ("KIT p.D816V" listed 2, `search_approvals(biomarker="KIT p.D816V")` returned none: both
  are imatinib for systemic mastocytosis *without* D816V; also `BCR::ABL1`, `17p deletion`).
  `approvals` now counts only rows that require the biomarker; the new
  `approvals_when_absent` counts the others, which `search_approvals(biomarker="NOT <name>")`
  now returns (#4).

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
