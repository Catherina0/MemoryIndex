# MemoryIndex - 核心信息速查

## 项目一句话
**基于 MIAP 代理协议的个人知识管理系统** + **现代化前后端 Web 应用**——用 AI 自动将互联网内容（视频、网页）转化为结构化可搜索的知识库，并提供美观的 Web 界面查询。

## 前后端系统（2025-03-18 新增）

### 🎨 前端应用（React）
- URL：http://localhost:3000
- 页面：首页（含统计+导入）、资料库、搜索、内容详情
- 技术：React 18 + TypeScript + Tailwind CSS
- 状态管理：Zustand
- 设计：Indigo 主色调、毛玻璃导航栏、卡片网格布局、自定义 CSS 组件类
- Dashboard 已合并到首页（/dashboard 自动重定向到 /）
- 首页”快速导入”支持粘贴分享文本，后端会自动提取链接并导入

### 📚 后端服务（FastAPI）
- URL：http://localhost:8000
- API 文档：http://localhost:8000/docs
- 功能：搜索、内容、标签、统计接口
- 数据库：集成现有 SQLite
- 若前端出现 `/api/*` 的 500 + Vite `ECONNREFUSED`，优先检查 8000 端口是否有后端进程

### ⚡ 快速启动
```bash
bash start-dev.sh  # 一键启动两个服务
```

### 📊 核心 API 端点

**导入类（前端直接调用，2026-03-19 新增）**
| 功能 | 端点 | 说明 |
|------|------|------|
| 下载视频（快速）| `POST /api/download-run` | 对应 `make download-run` |
| 下载视频（完整）| `POST /api/download-ocr` | 对应 `make download-ocr` |
| 归档网页（快速）| `POST /api/archive-run` | 对应 `make archive-run` |
| 归档网页（完整）| `POST /api/archive-ocr` | 对应 `make archive-ocr` |

**查询类（现有）**
| 功能 | 端点 |
|------|------|
| 搜索 | `GET /api/search?q=...` |
| 视频列表 | `GET /api/videos` |
| 网页列表 | `GET /api/archives` |
| 内容详情 | `GET /api/content/{id}` |
| 标签列表 | `GET /api/tags` |
| 统计数据 | `GET /api/stats` |

**前端简化流程**
- ✅ 前端自动检测 URL 类型（视频/网页）
- ✅ 前端根据 OCR 选项选择端点
- ✅ 前端仅发送 `{url}` 给后端
- ✅ 后端记录详细日志到 terminal

**请求示例**
```bash
# 方式1：curl 测试
curl -X POST http://localhost:8000/api/download-ocr \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=..."}'

# 方式2：前端表单
1. 打开 http://localhost:3000
2. 输入链接
3. 选择处理模式（快速/完整 OCR）
4. 点击导入
```

## 主要功能
| 功能 | 命令 | 说明 |
|------|------|------|
| **视频处理** | `make run Path=...` \| `make ocr Path=...` | 本地视频导入、转写、OCR、摘要 |
| **视频下载** | `make download URL=...` | 从 YouTube/Bilibili 下载视频 |
| **网页归档** | `make archive URL=...` | 保存网页到 Markdown + 数据库 |
| **全文搜索** | `make search Q="..."` | 秒级搜索所有内容 |
| **Cookie 管理** | `make login` | 一次性保存所有平台登录态 |
| **Telegram 控制** | `make tg-bot-setup` | 通过 Telegram 管理知识库 |
| **数据库操作** | `make db-stats` | 查看库存统计 |

## 关键 API 入口
| 模块 | 入口 | 用途 |
|------|------|------|
| **视频处理** | `core/process_video.py` `process_video()` | 完整视频处理流程 |
| **视频下载** | `core/video_downloader.py` `download_video()` | 下载视频到本地 |
| **网页提取** | `archiver/core/universal_archiver.py` `archive()` | 提取网页内容 |
| **搜索** | `db/repository.py` `SearchRepository.search()` | 全文搜索 |
| **索引** | `db/whoosh_search.py` `get_whoosh_index()` | 搜索索引维护 |

## 常见命令速查
```bash
# 系统启动
bash start-dev.sh                           # 一键启动前后端

# 测试新 API 端点（2026-03-19 新增）
node test_temp/20260319_frontend_logic_test.js  # 前端逻辑测试
python test_temp/20260319_test_new_api_endpoints.py  # 后端 API 测试
bash test_temp/20260319_demo_new_endpoints.sh  # 演示脚本

# 视频处理（最常用）
make run Path=~/Downloads/video.mp4        # 音频转写 + AI 摘要（快）
make ocr Path=~/Downloads/video.mp4        # OCR + 音频 + 摘要（慢，推荐）
make ocr Path=... OCR_WORKERS=4            # 指定并行进程数

# 视频下载
make download URL=https://youtube.com/...  # 下载视频
make download-run URL=...                  # 下载后自动处理（音频模式）
make download-ocr URL=...                  # 下载后自动处理（完整模式）

# 网页归档
make archive URL=https://zhihu.com/...     # 传统归档
make archive-run URL=...                   # 归档 + AI 报告
make archive-batch FILE=urls.txt           # 批量归档

# Cookie & 登录
make login                                 # 浏览器登录（保存所有 Cookie）
make list-cookies                          # 列出已保存的 Cookie
make delete-cookie DOMAIN=xiaohongshu.com  # 删除指定 Cookie
make url-clean URL="..."                   # 清理 URL 追踪器

# 搜索与查看
make search Q="关键词"                      # 全文搜索
make search-tags TAGS="标签1 标签2"        # 按标签搜索
make db-list [PAGE=1]                      # 列出所有视频
make db-show ID=1                          # 查看视频详情
make db-show ID=1 report                   # 查看报告
make db-show ID=1 transcript               # 查看转写文本

# 数据库管理
make db-stats                              # 完整统计
make db-init                               # 初始化数据库
make whoosh-rebuild                        # 重建搜索索引
make db-backup                             # 备份数据库

# Telegram Bot
make tg-bot-setup                          # 配置 Bot Token
make tg-bot-start                          # 启动 Bot（终端常驻）
make tg-bot-stop                           # 停止 Bot

# 环境
make setup                                 # 首次初始化（一次性）
make check                                 # 检查环境
make clean                                 # 清理输出文件
```

## 快捷别名
```bash
make s Q="..."                 # = make search Q="..."
make ls                        # = make db-list
make ls PAGE=2 LIMIT=50        # 分页查看（第2页，每页50条）
make show id=1                 # = make db-show ID=1
make report id=1               # = make db-show ID=1 report
make transcript id=1           # = make db-show ID=1 transcript
make show-ocr id=1             # = make db-show ID=1 ocr
make downrun URL=...           # = make download-run URL=...
make downocr URL=...           # = make download-ocr URL=...
```

## 环境配置
必需：`.env` 文件中的 **`GROQ_API_KEY`**（音频转写）

可选：
```
GEMINI_API_KEY=             # Google Gemini（用于摘要，自动备选）
TG_BOT_TOKEN=               # Telegram Bot Token
TG_ALLOWED_USER_ID=         # 限制 Bot 使用者
```

## 文件位置速查
| 内容 | 位置 |
|------|------|
| 配置 | `core/config.py` |
| 数据模型 | `db/models.py` |
| 数据库架构 | `db/schema.py` |
| 数据库操作 | `db/repository.py` |
| 主搜索接口 | `cli/search_cli.py` |
| SQL Schema | `db/schema.sql` |
| 后端主程序 | `backend/main.py` |
| 前端应用 | `frontend/src/App.tsx` |
| API 文档 | `Docs/BACKEND_API_GUIDE.md` |
| 前端指南 | `Docs/FRONTEND_GUIDE.md` |
| 使用手册 | `MANUAL.md` |

## 文档导航
| 文档 | 用途 |
|------|------|
| [MANUAL.md](MANUAL.md) | 📖 简单使用手册（推荐首先阅读） |
| [API.md](API.md) | 🔌 API 索引和模块速查 |
| [CHEATSHEET.txt](CHEATSHEET.txt) | ⌨️ 命令速查卡片 |
| [Docs/FRONTEND_GUIDE.md](Docs/FRONTEND_GUIDE.md) | 🎨 前端开发和架构 |
| [Docs/BACKEND_API_GUIDE.md](Docs/BACKEND_API_GUIDE.md) | 📚 后端 API 详解 |
| [Docs/FRONTEND_QUICKSTART.md](Docs/FRONTEND_QUICKSTART.md) | 🚀 前端快速启动指南 |
| [Report/20250318...](Report/20250318_frontend_backend_completion_report.md) | 📊 前后端完成报告 |

## 已知限制 & 特点
- **macOS 优先**：Vision OCR 原生支持，无需配置；其他系统需 PaddleOCR
- **单文件 <1000 行**：模块化设计，超限后需拆分
- **临时文件**：`test_fix/` 或 `test_temp/` 目录
- **git ignore**：`/Report/`、`/test_temp/` 已配置
- **数据库**：SQLite，位置 `storage/database/knowledge.db`
- **索引**：Whoosh，位置 `storage/whoosh_index/`
- **输出文件**：`docs/` 或 `output/` 目录

## Makefile 关键参数
| 参数 | 用途 | 示例 |
|------|------|------|
| `Path=` | 本地视频路径 | `make run Path=/Users/xxx/video.mp4` |
| `URL=` | 网页或视频链接 | `make archive URL=https://...` |
| `Q=` | 搜索关键词 | `make search Q="关键词"` |
| `ID=` | 视频或记录 ID | `make db-show ID=1` |
| `TAGS=` | 标签列表 | `make search-tags TAGS="标签1 标签2"` |
| `DET_MODEL=` | OCR 检测模型 | `make ocr Path=... DET_MODEL=server` |
| `OCR_WORKERS=` | 并行进程数 | `make ocr Path=... OCR_WORKERS=4` |
| `LLM=gemini` | 强制 Gemini 摘要 | `make run Path=... LLM=gemini` |
| `PAGE=` | 页码（分页） | `make db-list PAGE=2` |
| `LIMIT=` | 每页条数 | `make db-list LIMIT=50` |
| `FILE=` | 文件路径 | `make archive-batch FILE=urls.txt` |
| `SCREENSHOT_OCR=true` | 归档时 OCR 图片 | `make archive URL=... SCREENSHOT_OCR=true` |

## 平台支持
| 平台 | 支持状态 | 说明 |
|------|--------|------|
| YouTube | ✅ | 完全支持，需翻墙 |
| Bilibili | ✅ | 完全支持（需 BBDown） |
| 知乎 | ✅ | 完全支持（问答形式） |
| 小红书 | ✅ | 完全支持（需登录） |
| Reddit | ✅ | 完全支持（含评论） |
| Twitter/X | ✅ | 完全支持（需登录） |
| 通用网页 | ✅ | 任何 HTTP 页面 |

## 快速启动流程
```bash
# 1. 首次初始化（一次性）
make setup

# 2. 编辑 .env 填入 GROQ_API_KEY
nano .env

# 3. 处理第一个视频
make run Path=~/test.mp4

# 4. 或者归档网页
make login        # 先保存 Cookie
make archive URL=https://zhihu.com/question/xxx

# 5. 搜索
make search Q="关键词"

# 6. 查看统计
make db-stats
```

## 测试命令
```bash
make test                      # 基础环境测试
make test-vision-ocr          # 测试 Apple Vision OCR
make test-vision-ocr-image IMAGE=...  # 测试 OCR 效果
make db-test                  # 数据库测试
make selftest                 # 全功能自检
```

## 故障排查
| 问题 | 解决方案 |
|------|--------|
| 虚拟环境损坏 | `make setup`（自动重建） |
| 依赖缺失 | `make install` 或 `pip install -r requirements.txt` |
| 数据库无法访问 | `make db-init` 重新初始化 |
| 搜索无结果 | `make whoosh-rebuild` 重建索引 |
| Playwright 浏览器问题 | `make install-chromium` |
| 视频处理慢 | 使用 `make run` 代替 `make ocr`（跳过 OCR） |
