# MemoryIndex

**macOS 高性能知识库系统**  
*将视频和网页转化为可搜索的知识*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3+-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

MemoryIndex 是一个专为 macOS 优化的个人知识库构建工具。它能将视频（YouTube/Bilibili）和网页（知乎/Reddit/Twitter）自动转化为干净的 Markdown 文档，并提供毫秒级的全文检索。

## ✨ 核心功能

*   **🎬 视频到知识**：
    *   自动下载视频与音频。
    *   **macOS 原生 OCR**：使用 Apple Vision Framework 进行超高速、高精度的画面文字提取（无需安装笨重的 OCR 库）。
    *   **AI 摘要**：集成 Groq/Llama3 生成高质量摘要。
*   **🕸️ 网页协议归档器**：
    *   智能识别网页内容，去除广告与噪声。
    *   支持 Bilibili、Reddit、Twitter、知乎、小红书等平台。
*   **🔍 即时搜索**：
    *   基于 Whoosh 的本地全文检索引擎。
    *   支持中文分词与模糊搜索。

---

## 🚀 安装

> **注意**：本项目深度优化了 macOS 的原生能力（如 Vision OCR），目前仅推荐 macOS 用户使用。

### 前置要求
*   macOS 12+（Monterey 或更高版本）
*   Python 3.10+
*   `ffmpeg`（用于音视频处理）

```bash
brew install ffmpeg
```

### 设置

```bash
# 1. 克隆仓库
git clone https://github.com/Catherina0/MemoryIndex.git
cd MemoryIndex

# 2. 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
# macOS 用户（推荐，使用原生 Vision OCR）：
pip install -e .

# （可选）Linux/Windows 用户需要 PaddleOCR：
# pip install -e .[paddle] 
```

### 配置

在项目根目录创建 `.env` 文件：

```bash
cp .env.example .env  # 如果没有示例文件，直接创建即可
```

编辑 `.env` 填入必要的 API Key：

```ini
# .env file
GROQ_API_KEY=gsk_xxxxxxxxxxxxxx  # 用于视频摘要生成
```

---

## 📖 使用方法

MemoryIndex 使用 `make` 命令提供统一的操作接口。

### 1. 🎬 处理视频

下载视频、提取字幕、OCR 识别画面文字、生成 AI 摘要，最终输出 Markdown。

```bash
# 处理本地视频（仅音频转写）
make run VIDEO=/path/to/video.mp4

# 完整处理（音频 + OCR）
make ocr VIDEO=/path/to/video.mp4

# 下载并处理在线视频
make download-run URL="https://www.youtube.com/watch?v=example"
```

### 2. 🕸️ 归档网页

将网页转化为纯净的 Markdown 文档。

```bash
# 归档单个网页
make archive URL="https://zhuanlan.zhihu.com/p/123456"

# 归档并生成 AI 报告
make archive-run URL="https://zhuanlan.zhihu.com/p/123456"

# 批量归档（从文本文件读取 URL 列表）
make archive-batch FILE=urls.txt
```

支持的平台会自动识别（知乎、Bilibili、Reddit、Twitter、小红书等），通用 URL 会尝试提取正文。

### 3. 🔍 搜索知识

搜索所有已处理的视频和归档的网页。

```bash
# 关键词搜索
make search Q="神经网络"

# 按标签搜索
make search-tags TAGS="机器学习 深度学习"
```

### 4. 📈 统计信息

查看知识库当前的索引量和状态。

```bash
# 查看数据库统计
make db-stats

# 查看特定视频详情
make db-show ID=1
```

### 5. 🔧 环境管理

```bash
# 初始化环境（首次运行自动执行）
make setup

# 检查环境配置
make check

# 安装 PaddleOCR（非 macOS 用户）
make install-paddle-ocr

# 清理输出文件
make clean
```

### 💡 更多命令

运行 `make help` 查看所有可用命令。

---

### 📦 使用 `memidx` 命令（Homebrew 分发版本）

如果你通过 Homebrew 安装了 MemoryIndex，可以直接使用 `memidx` 命令：

```bash
# 处理视频
memidx run "https://www.youtube.com/watch?v=example"

# 归档网页
memidx archive "https://zhuanlan.zhihu.com/p/123456"

# 搜索知识
memidx search "神经网络"

# 查看统计
memidx stats
```

**注意**：`memidx` 命令仅在通过 `brew install memoryindex` 安装后可用。源码安装用户请使用上述 `make` 命令。

---

## 🛠️ 项目结构

*   `core/`：核心业务逻辑（视频处理、LLM 调用）。
*   `archiver/`：网页爬虫与清洗模块。
*   `db/`：数据库与全文索引管理。
*   `ocr/`：**macOS Vision OCR** 桥接代码（Swift/Python）。
*   `cli/`：命令行入口分发。

## ⚠️ 非 macOS 用户注意事项

虽然项目可以在 Linux/Windows 上运行部分功能（如网页归档），但核心的 **Vision OCR** 仅限 macOS。如果你在非 macOS 环境下使用 OCR 功能，必须安装 PaddleOCR 及其模型，且性能会低于 macOS 原生方案。

## 📄 许可证

GNU 通用公共许可证 v3.0
