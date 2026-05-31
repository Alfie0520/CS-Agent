#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <enterprises-json> <api-base-url> <api-key> [--dry-run]"
  echo "Example: $0 app/data/enterprises.json https://example.com change-me --dry-run"
  exit 1
fi

ENTERPRISE_JSON="$1"
API_BASE_URL="${2%/}"
API_KEY="$3"
DRY_RUN=false
if [ "${4:-}" = "--dry-run" ]; then
  DRY_RUN=true
fi

if [ ! -f "$ENTERPRISE_JSON" ]; then
  echo "Enterprise JSON not found: $ENTERPRISE_JSON"
  exit 1
fi

python3 -m json.tool "$ENTERPRISE_JSON" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/enterprises/data" \
  -H "X-API-Key: ${API_KEY}" \
  -F "dry_run=${DRY_RUN}" \
  -F "json_file=@${ENTERPRISE_JSON};type=application/json"
echo
