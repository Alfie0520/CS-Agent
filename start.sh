#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 自动安装/更新依赖
pip install -q -r requirements.txt

# 启动服务
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-80}"
