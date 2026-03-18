#!/bin/bash

# MemoryIndex 完整启动脚本
# 同时启动后端 API 服务和前端开发服务器

echo ""
echo "🚀 启动 MemoryIndex 系统..."
echo ""

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

# 检查虚拟环境
if [ ! -f "$VENV_PYTHON" ]; then
    echo "⚠️  警告: 虚拟环境不存在，使用系统 python"
    PYTHON_CMD="python"
else
    PYTHON_CMD="$VENV_PYTHON"
    echo "✅ 虚拟环境: $VENV_PYTHON"
fi

echo ""
echo "📚 启动后端 API 服务 (http://localhost:8000)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 启动后端 API
cd "$SCRIPT_DIR"
"$PYTHON_CMD" backend/main.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 检查后端是否成功启动
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo ""
    echo "❌ 后端启动失败！进程 $BACKEND_PID 已退出"
    echo "   请检查错误日志"
    exit 1
fi

if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo ""
    echo "⚠️  后端 API 端口可能已被占用"
    echo "   运行: lsof -ti:8000 | xargs kill -9"
    sleep 2
fi

echo ""
echo "⚛️  启动前端开发服务器 (http://localhost:3000)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# 等待前端启动
sleep 4

# 检查前端是否成功启动
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo ""
    echo "❌ 前端启动失败！进程 $FRONTEND_PID 已退出"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ MemoryIndex 系统已启动！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 访问地址："
echo "   🌐 前端: http://localhost:3000"
echo "   🔧 后端 API: http://localhost:8000"
echo "   📖 API 文档: http://localhost:8000/docs"
echo ""
echo "💡 快速操作："
echo "   1. 打开浏览器访问 http://localhost:3000"
echo "   2. 在首页输入视频或网页链接"
echo "   3. 选择处理模式（快速/完整）"
echo "   4. 点击导入开始处理"
echo ""
echo "🔍 后端进程ID: $BACKEND_PID"
echo "🔍 前端进程ID: $FRONTEND_PID"
echo ""
echo "❌ 按 Ctrl+C 停止所有服务"
echo ""

# 等待进程
wait
wait
