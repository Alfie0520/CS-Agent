#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

echo "== Enterprise data =="
curl -fsS \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  "${CS_AGENT_BASE_URL}/api/enterprises/data" \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); print({"success": r.get("success"), "count": r.get("count"), "source_path": r.get("source_path")})'

echo "== Asset stats =="
curl -fsS \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  "${CS_AGENT_BASE_URL}/api/assets/stats" \
  | json_pretty
