#!/usr/bin/env bash
# Run the agent UX evaluation: every task prompt x every agent CLI, each session in its own empty
# directory with only this MCP server mounted. See docs/benchmarks/agent-ux-protocol.md.
#
#   scripts/agent_ux_eval.sh <out-dir> [mcp-url] [task-glob]
#
# The server must already be running (python server.py --transport unified --port 18504).
# SLOT (optional) prefixes each session, e.g. a semaphore wrapper shared with other evaluations.
set -uo pipefail
OUT=${1:?usage: agent_ux_eval.sh <out-dir> [mcp-url] [task-glob]}
URL=${2:-http://127.0.0.1:18504/mcp}
HERE=$(cd "$(dirname "$0")" && pwd)
TASKS=${3:-"$HERE/../docs/benchmarks/tasks/[A-B]-*.md"}
mkdir -p "$OUT" && OUT=$(cd "$OUT" && pwd)
curl -sf "${URL%/mcp}/health" >/dev/null || { echo "server not reachable at $URL" >&2; exit 1; }
# agy has no per-session MCP flag: register (idempotent) in its user config.
agy mcp add eval-moalmanac-link "$URL" >/dev/null

# One session per agent at a time (3 concurrent): prompts run in sequence, agents in parallel.
for agent in claude codex agy; do
  ( for task in $TASKS; do ${SLOT:-} "$HERE/agent_ux_session.sh" "$agent" "$task" "$OUT" "$URL"; done ) &
done
wait
python3 "$HERE/agent_ux_scores.py" "$OUT"
