#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <local-images-dir> <ssh-target>" >&2
  echo "Example: $0 ./visit-images ubuntu@43.129.183.181" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

LOCAL_IMAGES_DIR="$1"
SSH_TARGET="$2"
REMOTE_ASSET_ROOT="${REMOTE_ASSET_ROOT:-/data/cs-agent-assets}"

if [ ! -d "$LOCAL_IMAGES_DIR" ]; then
  echo "Local images directory not found: ${LOCAL_IMAGES_DIR}" >&2
  exit 1
fi

echo "About to sync local folder to server with rsync --delete:" >&2
echo "  local:  ${LOCAL_IMAGES_DIR%/}/" >&2
echo "  remote: ${SSH_TARGET}:${REMOTE_ASSET_ROOT}/images/" >&2
echo "This makes the remote image folder match the local folder exactly." >&2

rsync -av --delete "${LOCAL_IMAGES_DIR%/}/" "${SSH_TARGET}:${REMOTE_ASSET_ROOT}/images/"

echo "Rescanning asset index..." >&2
curl -fsS -X POST "${CS_AGENT_BASE_URL}/api/assets/rescan" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  | json_pretty

echo "Current asset stats:" >&2
curl -fsS "${CS_AGENT_BASE_URL}/api/assets/stats" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  | json_pretty
