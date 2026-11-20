# moalmanac-link design (2026-11-20)

> Historical record — design as of 2026-11-20; the live tool catalog and README are authoritative.

Source of truth for scope: genefoundry-router
`docs/plans/2026-11-20-cancer-somatic-expansion.md` (§2 MOAlmanac row, §3 item 10, §4 DoD,
§5 item 6) and evidence report `I-moalmanac-decision.md`. Owner decision: MOAlmanac is its
own snapshot link (one source per link), not folded into civic-link.

## What MOAlmanac 2.0 is

A structured multi-agency **regulatory-approval** knowledge base (GA4GH VA-Spec model): every
statement is strength "Approval", predicate `predictsSensitivityTo`, direction `supports`.
Agencies: FDA, EMA, Health Canada, Ireland HSE (reimbursement), HPRA. Each statement cites a
versioned label document (publication date, regulatory ID, label URL). There are no trial,
guideline, resistance or prognostic tiers. It fills CIViC's gaps (e.g. KRAS G12C NSCLC).

## Data shipping

- Source: `vanallenlab/moalmanac-db` tag `v.2026-11-05` (commit `719ba8a5`; the same commit
  as `v.2026-08-02.1`), Zenodo DOI `10.5281/zenodo.23986188`, `referenced/*.json` (CC BY 4.0).
  The live API is rejected: draft branch, no paging, 1–28 MB answers, unknown filters ignored.
- `scripts/build_snapshot.py` fetches the pinned commit's tables, runs a **schema guard**
  (every table/field read, listed in `REQUIRED`; a gap aborts the build), keeps the 2,011
  active statements and joins them into one row per statement, plus indications, the
  biomarker vocabulary and a gene ID index. Output: one ~3 MB JSON + a provenance record
  (tag, commit, DOI, source sha256s, derived sha256, counts).
- Baked into the image (`data.mode: none`, two allowlisted `.json` files, each under the
  release gate's 4 MiB per-file allowlist cap). No data-init service, volume or network.
- Startup re-verifies the derived sha256 and the row schema (`snapshot.load()`); a mismatch
  stops the server.

## Tools (Tool-Naming v1.1, namespace `moalmanac`)

- `search_approvals(gene=, biomarker=, disease=, therapy=, agency=, response_mode=, limit=,
  offset=)` — AND filters, exact `total`/`truncated`, response_mode canon. Gene accepts a
  symbol, `HER2`/`PD-L1`/`PDL1` aliases, HGNC/Ensembl/NCBI IDs (resolved through the release's
  own gene mappings). Biomarker/disease/therapy match by tokens (`BRAF V600E` matches
  `BRAF p.V600E`; disease also by OncoTree or NCIt code; therapy also by brand).
- `get_indication(indication_id)` — fenced label text, dated agency history, label documents
  and the indication's statements.
- `list_biomarkers(gene=, biomarker_type=)` — the vocabulary with approval counts.
- `get_server_capabilities`, `get_diagnostics` (fleet discovery pair).

## Honesty rules

- A filter value that matches nothing in the release is `not_found` with `field` and a
  `next_commands` step (the behaviour gate's silent-empty rule). The message never echoes the
  value.
- An empty combination of recognised values returns `total: 0` and the message "No MOAlmanac
  approval found …", never "not approved".
- Alias expansion is the only addition: protein-expression markers link to their gene
  (HER2 → ERBB2, PD-L1 → CD274, ER → ESR1, …) except "Negative" markers, which mean the
  product is absent. Upstream gene links (e.g. "Wild type EGFR") are kept as curated.

## Known upstream defects (documented, not patched; tested)

1. EMA/HSE pemigatinib cholangiocarcinoma statements are bound to elacestrant.
2. FDA sotorasib + panitumumab for KRAS G12C CRC (Jan 2025) is missing.
3. "HER2-positive" and "ERBB2 amplification" are separate biomarkers.

Upstream issues are follow-ups for the owner (no contact with providers in this session).

## Out of scope

Live API proxying, openFDA freshness checks, resistance/trial tiers (not in the data), an
OncoTree hierarchy (no subtype expansion: `NSCLC` does not include `LUAD` rows), and an agent
UX evaluation (open follow-up).
