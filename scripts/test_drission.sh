#!/bin/bash
# 快速测试 DrissionPage 归档器

echo "🧪 测试 DrissionPage 归档器"
echo "============================"
echo ""

# 测试 URL（知乎）
TEST_URL="https://www.zhihu.com/question/20143381/answer/14060831"

echo "测试 URL: $TEST_URL"
echo ""

# 运行归档
make drission-archive URL="$TEST_URL"

echo ""
echo "============================"
echo "✓ 测试完成"
echo ""
echo "检查输出目录:"
ls -lh archived/
