# Agent UX evaluation protocol

How we test moalmanac-link the way it is used: real agent CLIs, each with only this MCP server
mounted, doing realistic and adversarial regulatory-approval lookups, then rating the
experience. It is adapted from pgscatalog-link's `docs/benchmarks/agent-ux-protocol.md`.

## Agents

Each prompt runs once per agent per round against one local server built from the checkout.
The three agents run in parallel, each working through the prompts in sequence, so at most 3
sessions run at a time. The server answers from its bundled snapshot with no upstream calls, so
speed ratings measure the server, not an upstream.

| Agent | Invocation (see `scripts/agent_ux_session.sh`) | Isolation |
|-------|-----------------------------------------------|-----------|
| Claude Code | `claude -p --model opus --strict-mcp-config --tools ""` | only this MCP; no built-in tools, user settings, hooks or plugins |
| Codex CLI | `codex exec --json -s read-only -c mcp_servers.<name>.url=...` | read-only sandbox, empty working directory |
| Antigravity (`agy`) | `agy -p` with the server added through `agy mcp add eval-moalmanac-link` | empty working directory; other user MCP servers stay mounted, the prompt forbids them |

`scripts/agent_ux_eval.sh <out> [url] [task-glob]` runs a round. Set `SLOT` to a semaphore
wrapper to share session slots with other evaluations; each session starts its wall clock after
the slot is acquired. Record the model each client resolved. Keep every session, including
failed or timed-out ones.

## Tasks

Prompts live in `tasks/` and are frozen before a round. `{SERVER}` is replaced by the mounted
name.

- `A-researcher.md`: KRAS G12C NSCLC approvals by agency with label version, date and
  regulatory ID; BRAF V600E melanoma across agencies; fenced label text and dated history of
  one indication; EGFR biomarkers in NSCLC; release, licence, citation and known limitations.
- `B-adversarial.md`: HER2 vs ERBB2 alias expansion and HER2-negative exclusion; `ER` must not
  match `HER2`; `V600` prefix vs `V600E`; the three known upstream defects (pemigatinib named
  elacestrant, missing sotorasib + panitumumab colorectal, the HER2/ERBB2 biomarker split);
  the NSCLC vs LUAD disease gap; wild-type biomarker rows under `gene=EGFR`; unknown and
  malformed indication IDs, an over-cap limit, a wrong-case agency, an HGNC ID; paging to the
  end; an empty combination that must read "no MOAlmanac approval found", never "not
  approved"; a patient treatment request (must disclaim); snapshot age.
- `C-fresh.md`: written and frozen before the final round and never shown earlier: ALK fusion
  vs ALK wild-type NSCLC, BRCA1/2 ovarian PARP inhibitors (germline vs somatic), tumour-agnostic
  MSI-H/dMMR/TMB-H, NTRK fusions, an unknown gene.

Agents get no answer key and no score target. A private answer key, verified against the
bundled snapshot before round 1, is kept with the run artefacts outside the repo.

## Ratings

Each session rates 9 categories as an integer 0-100 and justifies each with a concrete
interaction, then lists friction points and suggested improvements:

`discoverability`, `schema_clarity`, `correctness_confidence`, `completeness`,
`error_recovery`, `speed`, `token_efficiency`, `provenance_citation`, `overall_usability`.

`scripts/agent_ux_scores.py <round-dir>` parses the ratings and adds measured MCP calls, error
results, client tokens (Claude, Codex) and wall time. A missing rating counts as a failure.
A session whose trace has no error result cannot measure error recovery: its `error_recovery`
rating is shown in brackets and left out of the minimum. agy writes no trace, so its ratings
always count.

## Gate

A round passes when **every category's minimum over all sessions is >= 80**. Averages are
never used. It must also pass all of:

1. Every answer is audited against the answer key. A wrong fact the server caused (misleading
   field, dishonest count, an empty result read as "not approved") blocks the round whatever
   the self-ratings say.
2. The final round includes `C-fresh.md`.
3. `make ci-local` and the live conformance probes stay green.

## Improvement loop

1. Run the round (copy the runner first: editing a running bash script breaks it).
2. Triage the friction lists into server defects, missing affordances and evaluator noise.
   Fix defects; add an affordance only when several sessions or one blocking task need it.
   Do not tune wording to one prompt.
3. Review each change in ponytail style (the smallest complete change; a test per behaviour
   change) and run `make ci-local`.
4. Restart the server and rerun every prompt. Never drop a low-scoring session or reword a task
   to raise its score.

At most 5 rounds. The rounds and their scores are written up in `agent-ux-results.md`.
