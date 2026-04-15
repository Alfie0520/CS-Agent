#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 从 .env 读取 PORT（避免依赖 shell 环境变量，防止误杀 nginx）
APP_PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
APP_PORT="${APP_PORT:-8000}"

# 关闭已运行的旧 uvicorn 进程（只杀 uvicorn，不动 nginx）
OLD_PIDS=$(lsof -t -i :"$APP_PORT" 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
    echo "Stopping old process on port $APP_PORT (PID: $OLD_PIDS)..."
    kill $OLD_PIDS 2>/dev/null || true
    sleep 1
fi

# 激活虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# 自动安装/更新依赖
python3 -m pip install -q -r requirements.txt

# 后台启动服务
echo "Starting CS-Agent on port $APP_PORT..."
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$APP_PORT" > nohup.out 2>&1 &
APP_PID=$!

# 等待启动（最多 10 秒）
for i in $(seq 1 10); do
    if grep -q "Application startup complete" nohup.out 2>/dev/null; then
        echo "CS-Agent started successfully (PID: $APP_PID, port: $APP_PORT)"
        echo "Logs: tail -f $(pwd)/nohup.out"
        exit 0
    fi
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo "Process crashed! Check logs:"
        tail -30 nohup.out
        exit 1
    fi
    sleep 1
done

echo "Startup taking longer than expected, but process is running (PID: $APP_PID)"
echo "Logs: tail -f $(pwd)/nohup.out"
