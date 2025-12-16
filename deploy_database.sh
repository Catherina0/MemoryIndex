#!/bin/bash
# 数据库系统一键部署脚本
# 使用方法: ./deploy_database.sh

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          🗄️  数据库与搜索系统 - 一键部署                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    make ensure-venv
    echo ""
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖（如果需要）
echo "📦 检查依赖..."
pip install -q tabulate 2>/dev/null || true
echo "✅ 依赖检查完成"
echo ""

# 初始化数据库
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1/3: 初始化数据库"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make db-init
echo ""

# 运行测试
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2/3: 运行功能测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make db-test
echo ""

# 查看状态
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3/3: 检查系统状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
make db-status
echo ""

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 部署完成！                              ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 下一步："
echo ""
echo "1️⃣  处理视频（自动入库）："
echo "   make run VIDEO=video.mp4"
echo ""
echo "2️⃣  搜索内容："
echo "   make search Q=\"关键词\""
echo ""
echo "3️⃣  查看热门标签："
echo "   make db-tags"
echo ""
echo "4️⃣  查看完整帮助："
echo "   make help"
echo ""
echo "📚 文档：docs/DATABASE_QUICKSTART.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
