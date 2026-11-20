# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
