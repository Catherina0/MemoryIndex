#!/bin/bash

# MemoryIndex 完整启动脚本
# 同时启动后端 API 服务和前端开发服务器

echo "🚀 启动 MemoryIndex 系统..."

# 获取脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

# 终止前后台进程的函数
cleanup() {
    echo ""
    echo "🛑 停止服务..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup EXIT

# 启动后端 API
echo "📚 启动后端 API 服务 (http://localhost:8000)..."
if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠️  警告: 虚拟环境不存在，使用系统 python"
    python backend/main.py &
else
    "$VENV_PYTHON" backend/main.py &
fi
BACKEND_PID=$!
sleep 3

# 启动前端开发服务器
echo "⚛️  启动前端开发服务器 (http://localhost:3000)..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 系统已启动！"
echo ""
echo "📍 访问地址："
echo "   前端: http://localhost:3000"
echo "   后端 API: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "💡 按 Ctrl+C 停止所有服务"
echo ""

# 等待进程
wait
