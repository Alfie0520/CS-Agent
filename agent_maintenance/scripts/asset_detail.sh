#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <asset-id>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

ASSET_ID="$1"
ENCODED="$(url_encode "$ASSET_ID")"

curl -fsS \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  "${CS_AGENT_BASE_URL}/api/assets/${ENCODED}" \
  | json_pretty
