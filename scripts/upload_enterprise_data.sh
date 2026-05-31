#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <enterprises-json> <api-base-url> <api-key>"
  echo "Example: $0 app/data/enterprises.json https://example.com change-me"
  exit 1
fi

ENTERPRISE_JSON="$1"
API_BASE_URL="${2%/}"
API_KEY="$3"

if [ ! -f "$ENTERPRISE_JSON" ]; then
  echo "Enterprise JSON not found: $ENTERPRISE_JSON"
  exit 1
fi

python3 -m json.tool "$ENTERPRISE_JSON" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/enterprises/data" \
  -F "api_key=${API_KEY}" \
  -F "json_file=@${ENTERPRISE_JSON};type=application/json"
echo
