#!/bin/bash
# MemoryIndex 一键安装脚本

set -e

echo "🚀 MemoryIndex 安装程序"
echo "========================"
echo ""

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python 3，请先安装 Python 3.8 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ 检测到 Python $PYTHON_VERSION"

# 检测 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  未找到 ffmpeg，视频处理功能可能无法使用"
    echo "   推荐安装：brew install ffmpeg"
else
    echo "✓ 检测到 ffmpeg"
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "📦 开始安装 MemoryIndex..."
echo ""

# 选择安装模式
echo "请选择安装模式："
echo "  1) 开发模式（可编辑，适合开发）"
echo "  2) 用户模式（全局安装到用户目录）"
echo "  3) 系统模式（需要管理员权限）"
read -p "请输入选项 [1-3]: " choice

case $choice in
    1)
        echo "→ 使用开发模式安装..."
        pip3 install -e .
        ;;
    2)
        echo "→ 使用用户模式安装..."
        pip3 install --user .
        ;;
    3)
        echo "→ 使用系统模式安装..."
        pip3 install .
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "✅ 安装完成！"
echo ""
echo "🎉 现在你可以在任何地方使用以下命令："
echo ""
echo "  mi search '关键词'          # 搜索视频内容"
echo "  mi list                     # 列出所有视频"
echo "  mi topics                   # 查看所有主题"
echo "  mi-process video.mp4        # 处理视频"
echo ""
echo "💡 提示："
echo "  - 完整命令：memoryindex"
echo "  - 简写命令：mi"
echo "  - 查看帮助：mi --help"
echo ""

# 检查命令是否在 PATH 中
if ! command -v mi &> /dev/null; then
    echo "⚠️  警告：'mi' 命令未在 PATH 中找到"
    echo ""
    echo "请将以下行添加到你的 ~/.zshrc 或 ~/.bashrc："
    echo "  export PATH=\"\$PATH:$(python3 -m site --user-base)/bin\""
    echo ""
    echo "然后运行：source ~/.zshrc"
fi

echo "📖 查看完整文档：cat INSTALL.md"
