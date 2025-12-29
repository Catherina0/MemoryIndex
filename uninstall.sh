#!/bin/bash
# MemoryIndex 卸载脚本

set -e

echo "🗑️  MemoryIndex 卸载程序"
echo "========================"
echo ""

read -p "确定要卸载 MemoryIndex 吗？[y/N] " confirm

if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "已取消卸载"
    exit 0
fi

echo "→ 正在卸载..."
pip3 uninstall -y memoryindex || echo "未找到已安装的 memoryindex 包"

echo ""
echo "✅ 卸载完成"
echo ""
echo "注意：用户数据和配置文件未被删除："
echo "  - 数据库：./storage/"
echo "  - 视频输出：./output/"
echo "  - 配置文件：.env"
