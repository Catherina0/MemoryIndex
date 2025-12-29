# MemoryIndex 安装指南

## 快速安装（推荐）

### 方式一：使用 pip 直接安装

```bash
# 从源码安装
cd /path/to/knowledge
pip install -e .
```

安装后可以在任何位置使用：

```bash
# 搜索命令（完整版）
memoryindex search "关键词"

# 搜索命令（简写版）
mi search "关键词"

# 视频处理
mi-process video.mp4

# 查看帮助
mi --help
```

### 方式二：系统全局安装

```bash
# 构建包
python setup.py sdist bdist_wheel

# 安装到系统
pip install dist/memoryindex-1.0.0-py3-none-any.whl

# 或者直接安装
pip install .
```

### 方式三：创建独立可执行文件（开发模式）

```bash
# 在项目目录下
pip install -e .

# 现在可以全局使用
mi search "测试"
```

## 环境变量配置

创建 `~/.memoryindex.env` 或在项目根目录创建 `.env`：

```bash
# Groq API 配置（语音识别）
GROQ_API_KEY=your_api_key_here

# 数据库路径（可选，默认使用项目目录）
DB_PATH=/path/to/your/database.db

# OCR 配置
OCR_WORKERS=4
USE_GPU=false
```

## Homebrew 安装（高级）

如果你想创建真正的 Homebrew Formula：

### 1. 创建 Formula

```ruby
# /usr/local/Homebrew/Library/Taps/homebrew/homebrew-core/Formula/memoryindex.rb
class Memoryindex < Formula
  desc "智能视频知识库系统"
  homepage "https://github.com/Catherina0/MemoryIndex"
  url "https://github.com/Catherina0/MemoryIndex/archive/v1.0.0.tar.gz"
  sha256 "YOUR_SHA256_HERE"
  license "MIT"

  depends_on "python@3.11"
  depends_on "ffmpeg"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/mi", "--version"
  end
end
```

### 2. 发布到 GitHub Releases

```bash
# 打标签
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 创建发布包
python setup.py sdist

# 计算 SHA256
shasum -a 256 dist/memoryindex-1.0.0.tar.gz
```

### 3. 创建自定义 Tap（推荐）

```bash
# 创建你自己的 Homebrew Tap
brew tap Catherina0/memoryindex

# 安装
brew install memoryindex
```

## 验证安装

```bash
# 检查命令是否可用
which mi
mi --version

# 测试搜索功能
mi search "测试"

# 查看所有可用命令
mi --help
```

## 常见问题

### 1. 命令找不到

```bash
# 确认 pip 安装路径在 PATH 中
echo $PATH

# 找到 pip 的 bin 目录
python -m site --user-base

# 添加到 PATH（加入 ~/.zshrc 或 ~/.bashrc）
export PATH="$PATH:$(python -m site --user-base)/bin"
```

### 2. 权限问题

```bash
# 使用用户安装避免权限问题
pip install --user -e .
```

### 3. 虚拟环境冲突

```bash
# 先退出虚拟环境
deactivate

# 全局安装
pip install .
```

## 卸载

```bash
pip uninstall memoryindex
```

## 从开发模式切换到生产模式

```bash
# 开发模式（可编辑）
pip install -e .

# 生产模式（固定版本）
pip uninstall memoryindex
pip install .
```
