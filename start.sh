#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# 自动安装/更新依赖
python3 -m pip install -q -r requirements.txt

# 启动服务
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-80}"
