# moalmanac-link implementation plan (2026-11-20)

> Historical record — plan as executed on 2026-11-20 for v0.1.0; see the design spec in
> `docs/superpowers/specs/2026-11-20-moalmanac-link-design.md`.

1. Scaffold from `cbioportal-link` (itself a `pgscatalog-link` clone): rename, drop the live
   API client, rate limiter, URL guard and HTTP-policy suite (no runtime egress).
2. `scripts/build_snapshot.py` with the schema guard; build from `v.2026-11-05`; verify the
   GitHub fetch and a local checkout give byte-identical output.
3. Failing tests first: acceptance (KRAS G12C NSCLC, BRAF V600E melanoma), aliases, gene ID
   forms, unknown-value `not_found`, empty-result wording, paging honesty, response modes,
   the three upstream defects, schema guard (build + runtime + sha256).
4. `snapshot.py` + `service.py`, then the three tools, capabilities and diagnostics.
5. Docs (README, NOTICE CC BY 4.0, AGENTS, deployment), deploy overlay (`GF_IMAGE`, no
   project network), release allowlist, `identifiers.local.json`.
6. `make ci-local`, local container smoke + conformance probes, PR, review, release v0.1.0.
