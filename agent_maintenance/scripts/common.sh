#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "Missing required environment variable: ${name}" >&2
    echo "Set CS_AGENT_BASE_URL and CS_AGENT_API_KEY before running maintenance scripts." >&2
    exit 2
  fi
}

require_base_env() {
  require_env CS_AGENT_BASE_URL
  require_env CS_AGENT_API_KEY
  CS_AGENT_BASE_URL="${CS_AGENT_BASE_URL%/}"
}

json_pretty() {
  python3 -m json.tool
}

url_encode() {
  python3 - "$1" <<'PY'
from urllib.parse import quote
import sys
print(quote(sys.argv[1], safe=""))
PY
}
