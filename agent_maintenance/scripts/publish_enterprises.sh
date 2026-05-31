#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <enterprises-json>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

ENTERPRISE_JSON="$1"
if [ ! -f "$ENTERPRISE_JSON" ]; then
  echo "Enterprise JSON not found: ${ENTERPRISE_JSON}" >&2
  exit 1
fi

python3 -m json.tool "$ENTERPRISE_JSON" >/dev/null
echo "Validating first..."
"${SCRIPT_DIR}/validate_enterprises.sh" "$ENTERPRISE_JSON" >/dev/null

echo "Publishing enterprise data..."
curl -fsS -X POST "${CS_AGENT_BASE_URL}/api/enterprises/data" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  -F "dry_run=false" \
  -F "json_file=@${ENTERPRISE_JSON};type=application/json" \
  | json_pretty
