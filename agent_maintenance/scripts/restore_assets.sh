#!/usr/bin/env bash
# 从 /data/media_index.json 下载/校验全部图片到 /data/cs-agent-assets/images/，
# 然后 rescan 生成 asset_index.json。
#
# 适用场景：batch_image_operations.py 历史版本只调 /api/visit-image
# （仅写 media_index），导致客服 agent 查不到新图。可用此脚本一键重灌。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"
require_base_env

SSH_TARGET="${RESTORE_SSH_TARGET:-ubuntu@43.129.183.181}"
REMOTE_REPO="${REMOTE_REPO:-/opt/CS-Agent}"

echo "=== Step 1: ssh ${SSH_TARGET} → restore_wechat_material_assets.py ==="
ssh "${SSH_TARGET}" "cd ${REMOTE_REPO} && PYTHONPATH=${REMOTE_REPO} .venv/bin/python3 scripts/restore_wechat_material_assets.py"

echo
echo "=== Step 2: rescan asset_index ==="
curl -fsS -X POST "${CS_AGENT_BASE_URL}/api/assets/rescan" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  | json_pretty

echo
echo "=== Step 3: asset stats ==="
curl -fsS "${CS_AGENT_BASE_URL}/api/assets/stats" \
  -H "X-API-Key: ${CS_AGENT_API_KEY}" \
  | json_pretty
