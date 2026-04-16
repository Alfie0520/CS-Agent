#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# 从 .env 读取 PORT
APP_PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')
APP_PORT="${APP_PORT:-8000}"
PID_FILE=".cs-agent.pid"

# ---- 停止旧服务 ----
stop_old() {
    # 1. 通过 PID 文件杀
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Stopping old process (PID: $OLD_PID)..."
            kill "$OLD_PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # 2. 兜底：杀掉所有占用端口的进程
    fuser -k "$APP_PORT/tcp" 2>/dev/null || true

    # 3. 等待端口释放（最多 5 秒）
    for i in $(seq 1 5); do
        if ! fuser "$APP_PORT/tcp" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done

    # 4. 强制杀
    fuser -k -9 "$APP_PORT/tcp" 2>/dev/null || true
    sleep 1
}

stop_old

# ---- 虚拟环境 ----
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# ---- 安装依赖 ----
python3 -m pip install -q -r requirements.txt

# ---- 启动 ----
echo "Starting CS-Agent on port $APP_PORT..."
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$APP_PORT" >> nohup.out 2>&1 &
echo $! > "$PID_FILE"

# ---- 等待确认（最多 15 秒）----
for i in $(seq 1 15); do
    # 检查进程是否还活着
    if ! kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "FAILED! Process exited. Last logs:"
        tail -20 nohup.out
        rm -f "$PID_FILE"
        exit 1
    fi
    # 检查端口是否在监听
    if fuser "$APP_PORT/tcp" > /dev/null 2>&1; then
        echo "CS-Agent started successfully (PID: $(cat $PID_FILE), port: $APP_PORT)"
        echo "Logs: tail -f $(pwd)/nohup.out"
        exit 0
    fi
    sleep 1
done

echo "WARNING: Process running but port not yet bound. Check logs:"
echo "tail -f $(pwd)/nohup.out"
