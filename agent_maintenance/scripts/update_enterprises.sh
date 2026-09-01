#!/usr/bin/env bash
# update_enterprises.sh - 一键更新参访方案数据
#
# 用法：
#   ./agent_maintenance/scripts/update_enterprises.sh <excel-file>
#   ./agent_maintenance/scripts/update_enterprises.sh <excel-file> --skip-build   # 跳过 build
#   ./agent_maintenance/scripts/update_enterprises.sh --json <json-file>          # 已有 JSON
#
# 流程：
#   1) build_enterprise_db.py 把 Excel 转成 app/data/enterprises.json（除非 --skip-build）
#   2) validate_enterprises.sh dry-run 校验
#   3) 询问是否继续（除非 --yes）
#   4) publish_enterprises.sh 推送到服务器
#
# 依赖环境变量：
#   CS_AGENT_BASE_URL  例如 https://43.129.183.181
#   CS_AGENT_API_KEY   从运维获取
#
# 重要：这一步只更新企业数据，**不**自动重启服务。
#       服务每次请求都热加载 enterprises.json（见 app/enterprise_data.py 注释）。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_SCRIPT="${PROJECT_ROOT}/scripts/enterprise_db/build_enterprise_db.py"
JSON_PATH="${PROJECT_ROOT}/app/data/enterprises.json"

# ---------- 参数解析 ----------
SKIP_BUILD=0
AUTO_YES=0
JSON_INPUT=""

usage() {
  sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
  exit "${1:-0}"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help) usage 0 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --yes|-y) AUTO_YES=1 ;;
    --json) JSON_INPUT="${2:?--json 需要一个文件路径}"; shift 2 ;;
    -*) echo "Unknown option: $1" >&2; usage 2 ;;
    *)
      if [ -z "${JSON_INPUT}" ]; then
        # 第一个位置参数当作 Excel
        EXCEL_PATH="$1"
      else
        echo "Unexpected positional arg: $1" >&2; usage 2
      fi
      shift ;;
  esac
done

# ---------- 1. build ----------
if [ -n "${JSON_INPUT:-}" ]; then
  if [ ! -f "${JSON_INPUT}" ]; then
    echo "JSON file not found: ${JSON_INPUT}" >&2
    exit 1
  fi
  echo "==> 使用已有 JSON: ${JSON_INPUT}"
  TARGET_JSON="${JSON_INPUT}"
elif [ "${SKIP_BUILD}" -eq 1 ]; then
  if [ ! -f "${JSON_PATH}" ]; then
    echo "No existing ${JSON_PATH} and --skip-build given." >&2
    exit 1
  fi
  echo "==> 跳过 build，使用现有 ${JSON_PATH}"
  TARGET_JSON="${JSON_PATH}"
else
  if [ -z "${EXCEL_PATH:-}" ]; then
    echo "Error: 需要提供 Excel 文件路径（或用 --json <file>）" >&2
    usage 2
  fi
  # 转绝对路径
  case "${EXCEL_PATH}" in
    /*) ABS_EXCEL="${EXCEL_PATH}" ;;
    *)  ABS_EXCEL="${PROJECT_ROOT}/${EXCEL_PATH}" ;;
  esac
  if [ ! -f "${ABS_EXCEL}" ]; then
    echo "Excel file not found: ${ABS_EXCEL}" >&2
    exit 1
  fi
  # build_enterprise_db.py 硬编码读取 scripts/enterprise_db/data/2026游学资源表.xlsx
  EXPECTED_NAME="2026游学资源表.xlsx"
  EXPECTED_PATH="${PROJECT_ROOT}/scripts/enterprise_db/data/${EXPECTED_NAME}"
  if [ "${ABS_EXCEL}" != "${EXPECTED_PATH}" ]; then
    echo "==> Excel 路径不是 build 脚本预期的位置，临时复制到 ${EXPECTED_PATH}"
    mkdir -p "$(dirname "${EXPECTED_PATH}")"
    cp "${ABS_EXCEL}" "${EXPECTED_PATH}"
  fi
  echo "==> 步骤 1/3：从 Excel 生成 JSON"
  python3 "${BUILD_SCRIPT}"
  TARGET_JSON="${JSON_PATH}"
fi

# ---------- 2. validate ----------
echo
echo "==> 步骤 2/3：dry-run 校验"
"${SCRIPT_DIR}/validate_enterprises.sh" "${TARGET_JSON}"

# ---------- 3. 确认 ----------
if [ "${AUTO_YES}" -ne 1 ]; then
  echo
  read -r -p "校验通过，是否发布到服务器? [y/N] " ans
  case "${ans}" in
    y|Y|yes|YES) ;;
    *) echo "已取消，未发布。"; exit 0 ;;
  esac
fi

# ---------- 4. publish ----------
echo
echo "==> 步骤 3/3：发布到服务器"
"${SCRIPT_DIR}/publish_enterprises.sh" "${TARGET_JSON}"

echo
echo "==> 全部完成。服务无需重启，下次请求自动读到新数据。"
