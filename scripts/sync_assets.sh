#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <local-images-dir> <ssh-target> <api-base-url> <api-key>"
  echo "Example: $0 ./visit-images ubuntu@example.com https://example.com change-me"
  exit 1
fi

LOCAL_IMAGES_DIR="$1"
SSH_TARGET="$2"
API_BASE_URL="${3%/}"
API_KEY="$4"
REMOTE_ASSET_ROOT="${REMOTE_ASSET_ROOT:-/data/cs-agent-assets}"

if [ ! -d "$LOCAL_IMAGES_DIR" ]; then
  echo "Local images directory not found: $LOCAL_IMAGES_DIR"
  exit 1
fi

rsync -av --delete "${LOCAL_IMAGES_DIR%/}/" "${SSH_TARGET}:${REMOTE_ASSET_ROOT}/images/"
curl -fsS -X POST "${API_BASE_URL}/api/assets/rescan" -F "api_key=${API_KEY}"
echo
