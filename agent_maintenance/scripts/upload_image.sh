#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <category> <image-name> <local-image-path>" >&2
  echo "Example: $0 '16陕西' '西安比亚迪（展厅）.png' './西安比亚迪（展厅）.png'" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

CATEGORY="$1"
IMAGE_NAME="$2"
IMAGE_PATH="$3"

if [ ! -f "$IMAGE_PATH" ]; then
  echo "Image file not found: ${IMAGE_PATH}" >&2
  exit 1
fi

case "${IMAGE_NAME,,}" in
  *.jpg|*.jpeg|*.png|*.gif|*.bmp|*.webp) ;;
  *)
    echo "Unsupported image suffix in image name: ${IMAGE_NAME}" >&2
    exit 1
    ;;
esac

curl -fsS -X POST "${CS_AGENT_BASE_URL}/api/assets/image" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  -F "category=${CATEGORY}" \
  -F "image_name=${IMAGE_NAME}" \
  -F "image_file=@${IMAGE_PATH}" \
  | json_pretty
