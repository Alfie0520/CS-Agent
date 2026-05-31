#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 <query> [category]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

QUERY="$1"
CATEGORY="${2:-}"

curl -fsS -G "${CS_AGENT_BASE_URL}/api/assets/search" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  --data-urlencode "query=${QUERY}" \
  --data-urlencode "category=${CATEGORY}" \
  | json_pretty
