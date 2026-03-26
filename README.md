# MemoryIndex

**基于智能代理协议的知识库系统**
*用 AI 代理将互联网内容转化为结构化知识*

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3+-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

MemoryIndex 是一个基于 **MIAP（MemoryIndex 智能代理协议）** 的个人知识管理系统。通过专门化的 AI 代理角色，它能将视频（YouTube/Bilibili/小红书）和网页（知乎/Reddit/Twitter 等）自动转化为干净的 Markdown 文档，统一存储到 `/docs/` 文件夹，并提供毫秒级的全文检索。

## 特性

- **视频到知识**：自动下载、转写（Groq Whisper）、OCR（Apple Vision）、AI 摘要（Gemini/Groq LLM）
- **网页到知识**：智能内容提取、噪声过滤、平台适配（知乎/小红书/Reddit/Twitter/B站）
- **全文检索**：Whoosh + jieba 中文分词，毫秒级响应
- **现代化 Web 界面**：React 前端 + FastAPI 后端，支持搜索、浏览、导入、内容展示
- **Telegram Bot**：远程控制知识库
- **Cookie 管理**：支持从浏览器读取登录态，处理需认证内容

## 安装

```bash
# 一键安装（macOS）
curl -fsSL https://raw.githubusercontent.com/Catherina0/MemoryIndex/main/install.sh | bash

# 或手动安装
git clone https://github.com/Catherina0/MemoryIndex.git
cd MemoryIndex
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
brew install ffmpeg
```

## 配置

在项目根目录创建 `.env` 文件：

```ini
GROQ_API_KEY=gsk_xxxxxxxxxxxxxx    # 必需：音频转写
GEMINI_API_KEY=                     # 可选：AI 摘要
TG_BOT_TOKEN=                       # 可选：Telegram Bot
TG_ALLOWED_USER_ID=                  # 可选：限制 Bot 使用者
```

## 运行

```bash
# 启动 Web 前后端
bash start-dev.sh
# 前端: http://localhost:3000
# 后端 API 文档: http://localhost:8000/docs

# 处理视频
make run Path=~/Downloads/video.mp4        # 音频转写 + AI 摘要
make ocr Path=~/Downloads/video.mp4        # 完整模式（含 OCR）
make download-run URL=https://youtube.com/...  # 下载 + 处理

# 归档网页
make login                                  # 先保存 Cookie
make archive URL=https://zhihu.com/...      # 归档网页
make archive-run URL=...                    # 归档 + AI 报告
make archive-batch FILE=urls.txt            # 批量归档

# 搜索
make search Q="关键词"
make search-tags TAGS="标签1 标签2"

# 管理
make db-stats                               # 统计
make db-show ID=1                           # 查看详情
make whoosh-rebuild                         # 重建搜索索引
```

## 测试

```bash
make test                      # 基础环境测试
make test-vision-ocr           # 测试 Apple Vision OCR
make db-test                   # 数据库测试
make selftest                  # 全功能自检
make check                     # 检查环境配置
```

## 项目结构

```
MemoryIndex/
├── cli/                    # 命令行入口（main_cli / search_cli / archive_cli / db_stats / tg_bot）
├── core/                   # 核心业务逻辑
│   ├── process_video.py    # 视频处理全流程（转写/OCR/摘要/报告）
│   ├── archive_processor.py # 网页归档 LLM 处理（4 阶段报告生成）
│   ├── video_downloader.py # 多平台视频下载（yt-dlp/BBDown/XHS）
│   ├── config.py           # 全局配置
│   └── smart_frame_extractor.py # 智能抽帧
├── archiver/               # 网页归档模块
│   ├── core/               # 爬虫引擎（DrissionPage / Crawl4AI）
│   ├── platforms/           # 平台适配器（知乎/小红书/Reddit/Twitter/B站）
│   └── utils/              # Cookie / URL / 图片 / 浏览器管理
├── db/                     # 数据库层
│   ├── repository.py       # CRUD 仓库（Video/Archive/Tag/Stats）
│   ├── search.py           # 全文搜索引擎
│   ├── whoosh_search.py    # Whoosh + jieba 索引
│   ├── models.py           # 数据模型（Video/Artifact/Tag/Topic）
│   ├── schema.py           # 数据库初始化
│   └── tag_filters.py      # 噪声标签过滤
├── backend/                # FastAPI REST API（16 个端点）
│   ├── main.py             # API 入口
│   ├── services.py         # 业务逻辑（Search/Content/Stats/Import）
│   ├── models.py           # Pydantic 数据模型
│   ├── task_manager.py     # 异步任务管理
│   └── background_worker.py # 后台任务处理
├── frontend/               # React Web 应用
│   └── src/
│       ├── api/            # Axios API 客户端
│       ├── components/     # 7 个 UI 组件
│       ├── pages/          # 5 个页面（首页/资料库/搜索/详情/Dashboard）
│       └── store/          # Zustand 状态管理
├── ocr/                    # OCR 桥接（Vision / PaddleOCR）
├── scripts/                # 工具脚本（Cookie/URL清理/登录助手）
├── docs/                   # 生成的 Markdown 文档输出
├── Docs/                   # 项目开发文档
├── storage/                # 数据库 + 搜索索引
├── start-dev.sh            # 一键启动前后端
├── Makefile                # 统一命令接口
├── API.md                  # 模块索引与接口摘要
├── CLAUDE.md               # 协作规范
├── Plan.md                 # 项目规划
└── Remember.md             # 核心记忆
```

## Web 界面

### 快速启动

```bash
bash start-dev.sh
```

### 前端功能

- **首页**：知识库统计、快速导入（支持 URL 或分享文本，自动检测视频/网页类型）、最近内容、热门标签
- **资料库**：全部/视频/网页切换、标签筛选、排序、分页
- **搜索**：全文搜索、标签过滤
- **内容详情**：Markdown 渲染、多标签页（摘要/README/转写/OCR/报告）

### REST API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/search` | GET | 全文搜索 |
| `/api/videos` | GET | 视频列表 |
| `/api/archives` | GET | 网页列表 |
| `/api/content/{id}` | GET | 内容详情 |
| `/api/tags` | GET | 标签列表（自动过滤噪声标签） |
| `/api/stats` | GET | 统计信息 |
| `/api/import` | POST | 导入内容（URL 或分享文本） |
| `/api/tasks/{id}` | GET | 查询任务进度 |
| `/api/health` | GET | 健康检查 |

## 支持平台

| 平台 | 视频 | 网页 | 说明 |
|------|------|------|------|
| YouTube | 支持 | - | 需翻墙 |
| Bilibili | 支持 | 支持 | 需 BBDown |
| 小红书 | 支持 | 支持 | 需登录 |
| 知乎 | - | 支持 | 问答形式 |
| Reddit | - | 支持 | 含评论 |
| Twitter/X | - | 支持 | 需登录 |
| 通用网页 | - | 支持 | 任何 HTTP 页面 |

## 平台兼容性

### macOS（推荐）

- 完整功能，包括高性能 Vision OCR
- 零额外依赖，原生速度比 PaddleOCR 快 5-10 倍

### Linux/Windows

- 网页归档功能完整可用
- OCR 需安装 PaddleOCR：`pip install -e .[paddle]`

## 许可证 & 鸣谢

MemoryIndex 核心代码采用 [GNU 通用公共许可证 v3.0](LICENSE)。

特别鸣谢：
- **小红书下载与解析**：集成自开源项目 [XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader)（作者：JoeanAmier），遵循 GPL-3.0 协议。

**用 AI 代理构建你的第二大脑**
