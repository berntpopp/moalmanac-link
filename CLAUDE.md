# CLAUDE.md

**Read [AGENTS.md](AGENTS.md) first** — it is the authoritative contributor and agent guide.

Essentials:

- Read-only MCP server over a bundled, pinned MOAlmanac release snapshot (CC BY 4.0); no
  outbound requests. Rebuild data only with `scripts/build_snapshot.py`.
- Data plane returns plain dicts and raises typed errors; `run_mcp_tool` owns the envelope.
- Unknown filter values are `not_found` naming the parameter; empty results say "No MOAlmanac
  approval found", never "not approved". Never patch upstream data; document defects.
- FastMCP 4.x is post-training-cutoff: verify symbols against this repo's `.venv`.
- Gate: `make ci-local` (serialize it on shared machines). Never `gh release create`.
