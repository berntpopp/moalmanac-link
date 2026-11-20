# Agent UX evaluation results (2026-11-20)

Method: [`agent-ux-protocol.md`](agent-ux-protocol.md). Agents: Claude Code 2.1.329
(`claude-opus-5-5`), Codex CLI 0.164.0 (configured default `gpt-6-astra`, reasoning high),
Antigravity `agy` 1.5.13. Five rounds, the maximum. Rounds 1-2 ran A and B; the held-out C
was frozen before round 3 and ran in rounds 3-5. Raw traces are machine-local and are not
committed.

Codex hit its account usage limit during round 2 (B session, `rc=1`, kept, no ratings) and
could not run again the same day, so rounds 3-5 ran Claude and agy only. Codex's last full
ratings are rounds 1 and 2 (A).

## Minimum rating per category (0-100, over all sessions of the round)

| Round | Sessions | discov | schema | correct | complete | error | speed | tokens | provenance | overall |
|------:|---------:|------:|------:|------:|------:|------:|------:|------:|------:|------:|
| 1 (v0.1.0) | 6 (A, B x3) | 82 | 72 | 55 | 60 | 75 | 97 | 62 | 88 | 70 |
| 2 | 5 of 6 | 85 | 82 | 60 | 65 | 85 | 97 | 60 | 90 | 80 |
| 3 (+C) | 6 (A, B, C x Claude, agy) | 85 | 78 | 72 | 65 | 70 | 95 | 55 | 92 | 80 |
| 4 | 6 | 88 | 78 | 72 | 65 | 85 | 97 | 70 | 93 | 82 |
| 5 | 6 | 85 | 82 | 72 | 65 | 85 | 97 | 60 | 95 | 82 |

In round 5 every agy rating is 84 or higher (completeness 84-88, everything else 85-100).
All the round-5 minimums below 80 come from Claude: correctness 72 and completeness 65 from
its B session, token efficiency 60 (B) and 75 (C), completeness 78 (A).

**Gate not reached (>= 80 everywhere).** The three blocking categories, with their causes:

- **Correctness (72) and completeness (65): mostly upstream data.** Claude's B ratings cite
  the same records every round: EMA and HSE pemigatinib statements name elacestrant, FDA
  sotorasib + panitumumab for colorectal cancer is missing, the FDA sotorasib status says
  "Approved" while its label says accelerated, there is no KRAS G12D biomarker, and OncoTree
  subtypes (LUAD) are not mapped to the NSCLC level MOAlmanac curates at. The server serves
  the pinned release as-is by design (no patching of upstream values); it now flags each
  defect on the affected rows, so agents found and caveated all of them. Claude asks for
  corrected values; that would change the data contract and is not done here.
- **Token efficiency (60): payload size on broad queries.** Claude's B session pages
  `gene=HER2, disease=breast` (228 rows) at `limit=100`. `limit=0` with `summary` (added in
  round 3) answers count questions in about 1 KB, and agy rates tokens 88-90 using it.

## Answer audit

Every answer was checked against a private answer key verified against the bundled snapshot
before round 1. No session in any round stated a wrong fact caused by the server, and none
read an empty result as "not approved".

Round 4 failed the audit anyway: pages after the first carried the empty-result message "No
MOAlmanac approval found" while returning rows (introduced in round 3 with the first-page-only
summary). Agents noticed it as spurious. It was fixed before round 5, and round 5 is clean.

Agents also found four upstream defects that were not in the register (Lumakras status,
Datroway disease mapping, Lazcluze label fields, Tagrisso regimens without pemetrexed). All
four were verified against the snapshot and added.

## Fixes made

| Round | Friction | Change |
|------:|----------|--------|
| 1 | "breast cancer" was `not_found`; "ovarian cancer" matched 2 of 57 rows | generic disease words (cancer, carcinoma, tumour, neoplasm) are ignored |
| 1 | disease/biomarker `not_found` offered only an empty search | closest vocabulary names with ready retries (`candidates`), keeping other filters |
| 1 | an exact vocabulary name also matched longer names | an exact `list_biomarkers` name matches only that biomarker |
| 1 | HSE pemigatinib unreachable by `therapy=` | therapy also matches the label name |
| 1 | per-agency and regimen counts tallied by hand | `summary` over all matches |
| 1 | defects only in capabilities | `known_defects` on affected rows and `get_indication` |
| 1 | `get_indication("lumakras")`, `agency="FDA"` gave no usable retry | suggested IDs; case-corrected retry |
| 2 | wild-type eligibility rows dominate gene searches | `search_approvals(biomarker_type=)` |
| 2 | 280-char message cap cut the suggestion list; flags lost in minimal mode | names in a structured field; `known_defects` in every mode |
| 3 | the structured suggestion field was dropped by the envelope | fleet `candidates` field; gene and therapy suggestions |
| 3 | count questions needed full pages | `limit=0` returns only `total` and `summary`; summary on the first page only |
| 4 | later pages said "No MOAlmanac approval found" | message only when `total == 0`; `limit=0` next step fetches rows |
| 4 | defect rows counted silently in summaries | `summary.known_defect_rows` |

## Remaining friction

- OncoTree subtype codes are not mapped to parent terms (LUAD -> NSCLC). MOAlmanac records
  most lung indications at NSCLC; the disease description and error now say so.
- Biomarker families are not expanded (`NTRK`, `BRCA`); `candidates` names the members.
- `v::ALK` also tags atezolizumab "after ALK therapy" statements. Telling them apart needs
  the label text (`get_indication`); MOAlmanac has no biomarker-role field.
- EMA and Health Canada rows have no `regulatory_id` upstream.
