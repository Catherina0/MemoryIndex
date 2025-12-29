#!/bin/bash
# Homebrew 发布快速命令
# 这个脚本包含所有需要执行的命令，可以复制粘贴使用

echo "📦 Homebrew 发布命令速查"
echo "================================"
echo ""

cat << 'COMMANDS'

# ============================================
# 第一步：提交代码并创建标签
# ============================================

cd /Users/catherina/Documents/GitHub/knowledge

# 查看状态
git status

# 提交所有更改
git add .
git commit -m "Release v1.0.0: Add Homebrew support with memidx command"

# 推送到 GitHub
git push origin main

# 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0 - First stable release"

# 推送标签
git push origin v1.0.0


# ============================================
# 第二步：创建 GitHub Release
# ============================================

# 在浏览器打开：
open https://github.com/Catherina0/MemoryIndex/releases/new

# 填写信息：
# - Tag: v1.0.0
# - Title: v1.0.0 - MemoryIndex First Stable Release
# - Description: 见 HOMEBREW_GUIDE.md 中的模板
# 然后点击 "Publish release"


# ============================================
# 第三步：下载并计算 SHA256
# ============================================

# 创建临时目录
mkdir -p ~/homebrew-release
cd ~/homebrew-release

# 下载源码包
curl -L -o memoryindex-1.0.0.tar.gz \
  https://github.com/Catherina0/MemoryIndex/archive/refs/tags/v1.0.0.tar.gz

# 计算 SHA256（复制这个值！）
shasum -a 256 memoryindex-1.0.0.tar.gz


# ============================================
# 第四步：创建 Homebrew Tap
# ============================================

# 1. 在 GitHub 创建新仓库：
open https://github.com/new
# 仓库名：homebrew-memoryindex
# 类型：Public
# 初始化 README

# 2. 克隆仓库
cd ~/Documents/GitHub
git clone https://github.com/Catherina0/homebrew-memoryindex.git
cd homebrew-memoryindex

# 3. 创建 Formula 目录
mkdir -p Formula


# ============================================
# 第五步：创建 Formula
# ============================================

# 复制 Formula 模板
cp /Users/catherina/Documents/GitHub/knowledge/Formula.rb \
   ~/Documents/GitHub/homebrew-memoryindex/Formula/memoryindex.rb

# 编辑 Formula（替换 SHA256）
nano Formula/memoryindex.rb
# 在 sha256 行替换成你在第三步计算的值


# ============================================
# 第六步：提交 Formula
# ============================================

cd ~/Documents/GitHub/homebrew-memoryindex

# 提交
git add Formula/memoryindex.rb
git commit -m "Add memoryindex formula v1.0.0"
git push origin main

# 更新 README
cat > README.md << 'EOF'
# Homebrew Tap for MemoryIndex

智能视频知识库系统的 Homebrew Tap

## 安装

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

## 使用

```bash
memidx search "关键词"
memidx list
memidx-process video.mp4
memidx --help
```

## 更多信息

- 项目：https://github.com/Catherina0/MemoryIndex
- 文档：https://github.com/Catherina0/MemoryIndex/blob/main/README.md
EOF

git add README.md
git commit -m "Update README"
git push origin main


# ============================================
# 第七步：测试安装
# ============================================

# 添加 Tap
brew tap Catherina0/memoryindex

# 检查 Formula
brew info memoryindex
brew audit --strict memoryindex

# 安装
brew install memoryindex

# 测试
which memidx
memidx --help
memidx list --limit 5

# 如果有问题，卸载重装
brew uninstall memoryindex
brew install --build-from-source memoryindex


# ============================================
# 完成！
# ============================================

echo "✅ 发布完成！"
echo ""
echo "用户现在可以这样安装："
echo "  brew tap Catherina0/memoryindex"
echo "  brew install memoryindex"
echo ""
echo "使用："
echo "  memidx search '关键词'"

COMMANDS
