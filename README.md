# MemoryIndex

**基于智能代理协议的知识库系统**  
*用 AI 代理将互联网内容转化为结构化知识*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3+-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

MemoryIndex 是一个基于 **MIAP（MemoryIndex 智能代理协议）** 的个人知识管理系统。通过专门化的 AI 代理角色，它能将视频（YouTube/Bilibili）和网页（知乎/Reddit/Twitter 等）自动转化为干净的 Markdown 文档，统一存储到 `/docs/` 文件夹，并提供毫秒级的全文检索。

## 🚀 极速一键安装 (macOS 专属)

打开 macOS 的 Terminal（终端），直接粘贴以下命令执行：

```bash
curl -fsSL https://raw.githubusercontent.com/Catherina0/MemoryIndex/main/install.sh | bash
```

*此脚本会自动帮你：克隆项目仓库、通过 Homebrew 安装必需的系统依赖（Python 3.11, ffmpeg 等）、创建独立的虚拟环境、安装所有 Python 依赖与 Playwright 浏览器，并最终完成数据库初始化构建！*

安装结束后，请查看目录下的 `.env` 文件，填入你的 `GROQ_API_KEY` 及其他可能的设定值，即可立即使用 `make` 命令开启知识获取之旅。

---

## 🧠 设计理念：智能代理协议 (MIAP)

MemoryIndex 采用**角色化 AI 代理系统**，每个代理负责特定的知识转换任务：

*   **🕸️ 通用网页归档员**：专注网页内容提取，去除噪声，输出纯净 Markdown
*   **🎬 智能视频处理器**：从视频中提取视觉（OCR）和听觉（转录）信息，生成结构化文本
*   **📚 知识库管理员**：维护 Whoosh 全文索引，提供快速搜索
*   **🏗️ 系统架构师**：确保项目可安装、可维护、可分发

所有处理后的 Markdown 文档统一输出到 `/docs/` 文件夹，便于版本控制和跨平台同步。

> 详细的代理协议定义请参阅 [agents.md](agents.md)

## ✨ 核心功能

### 🎬 视频到知识（智能视频处理器）
*   **多维度提取**：自动下载视频，同时处理视觉（OCR）和听觉（转录）信息
*   **macOS 原生 OCR**：使用 Apple Vision Framework 进行超高速、高精度的画面文字提取
*   **AI 认知摘要**：集成 Groq/Llama3 将 OCR + 转录文本合成为连贯的结构化摘要
*   **输出格式**：生成标准化 Markdown，统一存储到 `/docs/` 文件夹

### 🕸️ 网页到知识（通用网页归档员）
*   **智能内容提取**：使用平台特定 CSS 选择器精确隔离核心内容
*   **噪声过滤**：自动去除评论、侧边栏、广告和推荐内容
*   **平台支持**：知乎、Bilibili、Reddit、Twitter、小红书 + 通用网页
*   **Cookie 管理**：支持从本地浏览器读取认证信息，处理需登录的内容

### 🔍 知识检索（知识库管理员）
*   **全文索引**：基于 Whoosh 的本地搜索引擎，毫秒级响应
*   **中文优化**：集成 jieba 分词，支持中文模糊搜索
*   **增量更新**：自动检测 `/docs/` 文件夹变化，智能更新索引

### 🏗️ 系统架构（系统架构师）
*   **模块化设计**：`cli`、`core`、`archiver`、`ocr`、`db` 清晰分离
*   **一键安装**：支持 Homebrew Formula 和 PyPI 包分发
*   **测试隔离**：临时测试和修复脚本统一存放在 `test_fix/` 目录

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

MemoryIndex 使用 `make` 命令提供统一的操作接口。当你运行命令时，相应的 AI 代理会被激活执行任务。

### 代理工作流示例

当你运行 `memidx [url]` 时：
1.  **系统架构师** 确保 CLI 路由命令
2.  **路由器** 判断 URL 类型（网页 or 视频）
3.  **对应代理** 执行提取，生成 Markdown 到 `/docs/`
4.  **知识库管理员** 自动检测新文件，更新索引
5.  用户可通过 `memidx search` 查询结果

### 1. 🎬 处理视频（激活视频处理器代理）

视频处理器会下载视频、提取字幕、OCR 识别画面文字、生成 AI 摘要，最终输出 Markdown 到 `/docs/`。

```bash
# 处理本地视频（音频转写）
make run VIDEO=/path/to/video.mp4

# 完整处理（音频 + 视觉 OCR）
make ocr VIDEO=/path/to/video.mp4

# 下载并处理在线视频
make download-run URL="https://www.youtube.com/watch?v=example"
```

**输出**：生成的 Markdown 文件会保存到 `/docs/` 文件夹，包含标题、摘要、时间戳和完整文本。

### 2. 🕸️ 归档网页（激活网页归档员代理）

归档员会识别平台类型，提取核心内容，去除噪声，输出纯净 Markdown 到 `/docs/`。

```bash
# 归档单个网页
make archive URL="https://zhuanlan.zhihu.com/p/123456"

# 归档并生成 AI 增强报告
make archive-run URL="https://zhuanlan.zhihu.com/p/123456"

# 批量归档（从 urls.txt 读取）
make archive-batch FILE=urls.txt
```

**支持平台**：知乎、Bilibili、Reddit、Twitter、小红书 + 通用网页（自动识别）

**Cookie 支持**：自动从 Chrome/Edge 读取登录状态，处理需要认证的内容

### 3. 🔍 搜索知识（查询知识库管理员）

知识库管理员维护的全文索引可以快速检索所有 `/docs/` 中的内容。

```bash
# 关键词搜索
make search Q="神经网络"

# 按标签搜索
make search-tags TAGS="机器学习 深度学习"
```

**特性**：
*   支持布尔运算符（AND、OR、NOT）
*   支持模糊匹配和通配符
*   返回结果带高亮片段

### 4. 📈 统计与管理

```bash
# 查看知识库统计（文档数、索引大小）
make db-stats

# 查看特定文档详情
make db-show ID=1

# 重建索引（当 /docs/ 文件夹有外部修改时）
make reindex
```

### 5. 🔧 环境管理

```bash
# 初始化环境（首次运行）
make setup

# 检查环境配置（验证 API Key、依赖等）
make check

# 安装 PaddleOCR（非 macOS 用户）
make install-paddle-ocr

# 清理临时文件
make clean
```

### 💡 更多命令

运行 `make help` 查看所有可用命令及其说明。

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

```
MemoryIndex/
├── agents.md              # MIAP 智能代理协议定义
├── cli/                   # 命令行入口和路由分发
├── core/                  # 核心业务逻辑（视频处理、LLM 调用）
├── archiver/              # 网页归档员模块
│   ├── platforms/         # 平台特定的提取策略
│   ├── core/              # 爬虫引擎（Crawl4AI/Playwright）
│   └── utils/             # Cookie 管理、内容清洗
├── ocr/                   # 视频处理器的 OCR 桥接
│   ├── vision_ocr.swift   # macOS Vision Framework 桥接
│   └── paddle_fallback.py # 非 macOS 平台的 PaddleOCR
├── db/                    # 知识库管理员的索引存储
│   └── whoosh_index/      # Whoosh 全文索引文件
├── docs/                  # 🎯 统一输出目录（所有 Markdown 文件）
│   ├── videos/            # 视频处理结果
│   └── archived/          # 网页归档结果
├── test_fix/              # 临时测试和修复脚本（已加入 .gitignore）
├── Formula/               # Homebrew 分发配置
└── Makefile               # 统一命令接口
```

**关键目录说明**：
*   `/docs/`：所有生成的 Markdown 文档的最终存储位置，便于版本控制和同步
*   `/archiver/platforms/`：包含知乎、Reddit、Twitter 等平台的 CSS 选择器映射表
*   `/ocr/`：macOS 使用 Swift 原生 Vision OCR，其他平台回退到 PaddleOCR
*   `/test_fix/`：开发过程中的临时脚本，不会被 Git 跟踪

## ⚠️ 平台兼容性说明

### macOS 用户（推荐）
*   ✅ **完整功能**：包括高性能 Vision OCR
*   ✅ **零额外依赖**：无需安装 OCR 模型或库
*   ✅ **原生速度**：OCR 性能比 PaddleOCR 快 5-10 倍

### Linux/Windows 用户
*   ⚠️ **有限支持**：网页归档功能完整可用
*   ⚠️ **OCR 性能**：需安装 PaddleOCR（约 500MB 模型），速度较慢
*   💡 **推荐场景**：主要用于网页归档，视频处理建议在 macOS 上进行

**安装 PaddleOCR（非 macOS）**：
```bash
pip install -e .[paddle]
```

---

## 📄 许可证

本项目采用 [GNU 通用公共许可证 v3.0](LICENSE)。

**用 AI 代理构建你的第二大脑 🧠**
