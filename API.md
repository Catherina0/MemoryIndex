# MemoryIndex - API 索引与接口摘要

> 优先查看此文件定位模块和入口。**按 Makefile 功能分类**，快速定位所有模块与命令。

---

## 🌐 Web 前后端系统 API【新】

### 快速访问

| 功能 | 地址 |
|------|------|
| 前端应用 | http://localhost:3000 |
| API 文档 | http://localhost:8000/docs |
| 搜索接口 | http://localhost:8000/api/search |
| 统计数据 | http://localhost:8000/api/stats |

### backend/main.py - FastAPI 服务

**职责**：REST API 服务，支持搜索、内容管理、统计

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/search` | GET | 全文搜索（q, tags, source_type, limit, offset） |
| `/api/videos` | GET | 列出视频（limit, offset, sort） |
| `/api/archives` | GET | 列出网页（limit, offset, sort） |
| `/api/content/{id}` | GET | 获取内容详情（content_type=video/archive） |
| `/api/tags` | GET | 获取所有标签（limit） |
| `/api/stats` | GET | 统计信息（total_videos, total_archives, top_tags） |
| `/api/health` | GET | 健康检查 |

**参数示例**：
```bash
# 搜索
curl "http://localhost:8000/api/search?q=ai&tags=技术&limit=20&offset=0"

# 获取第一个视频的详情
curl "http://localhost:8000/api/content/1?content_type=video"

# 获取统计
curl "http://localhost:8000/api/stats"
```

### frontend/ - React Web 应用

**职责**：现代化 Web 界面，支持搜索、浏览、统计

| 页面 | URL | 功能 |
|------|-----|------|
| 首页 | `/` | 知识库概览、统计、最近内容 |
| 搜索 | `/search` | 全文搜索、标签过滤、分页 |
| 详情 | `/content/{id}` | 完整内容（转写、OCR、报告） |
| 统计 | `/dashboard` | 数据统计和分析 |

**技术栈**：React 18 + TypeScript + Tailwind CSS + Zustand + Axios

**核心文件**：
- `src/api/client.ts` - API 请求客户端
- `src/components/` - UI 组件
- `src/pages/` - 页面组件
- `src/store/` - Zustand 状态管理

---

## 📹 视频处理模块


### core/process_video.py - 核心视频处理

**职责**：视频转写、OCR、AI 摘要、报告生成、数据库存储

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `process_video()` | `video_path: Path, with_ocr: bool=False, ...` | `dict` | 完整流程：音频提取→转写→OCR→摘要→报告→存储 |
| `transcribe_audio_with_groq()` | `audio_path: Path, model_type: str='v3'` | `dict` | Groq Whisper（支持 v3 和 turbo） |
| `summarize_with_gemini()` | `full_text: str, use_oss: bool=False` | `tuple[str, int]` | LLM 摘要（Gemini 或 OSS 120B） |
| `generate_detailed_content()` | `full_text: str` | `tuple[str, int]` | 结构化详细内容 |
| `extract_frames()` | `video_path: Path, frames_dir: Path` | `None` | 视频抽帧 |
| `generate_formatted_report()` | `full_text: str, timeline: list, output_path: Path` | `str` | 最终 Markdown 报告 |
| `save_to_database()` | `title: str, content_hash: str, file_path: str, ...` | `int \| None` | 存储到数据库 |

**Makefile 命令**：
```bash
make run Path=视频路径                    # 音频模式（快）
make ocr Path=视频路径                    # 完整模式（含 OCR）
make ocr Path=... DET_MODEL=server       # 使用更强 OCR 模型
make ocr Path=... OCR_WORKERS=4          # 并行进程数
makecore/video_downloader.py - 视频下载器

**职责**：下载 YouTube、Bilibili 等平台视频

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `download_video()` | `url: str, output_dir: Path='videos', force: bool=False` | `Path` | 下载视频 |
| `detect_platform()` | `url: str` | `str` | 检测平台类型 |

**Makefile 命令**：
```bash
make download URL=链接                   # 仅下载
make download-run URL=链接               # 下载后音频处理
make download-ocr URL=链接               # 下载后完整处理
```

**依赖**：yt-dlp, BBDownideo_downloader.py - 视频下载器

**职责**：下载 YouTube、Bilibili 等平台视频

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `download_video()` | `url: str, output_dir: str \| Path = "videos", ...` | `Path` | 下载视频，返回本地文件路径 |
| `detect_platform()` | `url: str` | `str` | 检测 URL 属于哪个平台（youtube/bilibili/local/unknown） |
 🌐 网页归档模块

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `archive()` | `url: str, cookies: dict=None, visible: bool=False` | `dict` | 归档单个 URL |
| `archive_batch()` | `urls: List[str], cookies: dict=None` | `List[dict]` | 批量归档 |
| `detect_platform()` | `url: str` | `str` | 检测平台类型 |

**支持平台**：知乎、小红书、Bilibili、Reddit、Twitter/X、通用网页

**Makefile 命令**：
```bash
make archive-batch FILE=urls.txt         # 从文件批量归档
make url-clean URL="链接"                # 反追踪 + 短链还原
```

**文件位置**：[archiver/core/universal_archiver.py](archiver/core/universal_archiver.py), [archiver/platforms/](archiver/platforms/)

---

## 🍪 Cookie & 登录管理

### scripts/cookie_manager.py - Cookie 统一管理

**职责**：从浏览器读取、保存、删除 Cookie

|  🔍 搜索与数据库模块

###file 命令 | 功能 |
|--------------|------|
| `make login` | 启动浏览器登录（保存所有平台 Cookie） |
| `make list-cookies` | 列出已保存的所有 Cookie |
| `make delete-cookie DOMAIN=xiaohongshu.com` | 删除指定 Cookie |
| `make clear-cookies` | 清除所有 Cookie |
| `make login-twitter` | 推特专用登录 |
| `make reset-b CRUD 操作

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `search()` | `query: str, tags: List[str]=None, limit: int=10` | `List[SearchResult]` | 全文搜索 |
| `get_by_id()` | `id: int` | `Video \| Archive \| None` | 按 ID 查询 |
| `get_all_videos()` | `limit: int=100, offset: int=0` | `List[Video]` | 列出所有视频 |
| `get_all_archives()` | `limit: int=100, offset: int=0` | `List[Archive]` | 列出所有存档 |
| `add_video()` | `video: Video` | `int` | 新增视频 |
| `add_archive()` | `archive: Archive` | `int` | 新增存档 |
| `update_tags()` | `record_id: int, tags: List[str]` | `bool` | 更新标签 |
| `delete_by_id()` | `id: int, source_type: SourceType` | `bool` | 删除记录
| 追踪器移除 | 删除 `utm_*`, `fbclid`, `gclid` 等 |
| 短链还原 | 展开 `bit.ly`, `tinyurl`, `ow.ly` 等 |
| 文本提取 | 从分享文本自动提取 URL |

**Makefile 命令**：
```bash
make url-clean URL="https://example.com?utm_source=xxx"
```

**文件位置**：[scripts/url_cleaner.py](scripts/url_clean

---

### archiver/core/universal_archiver.py - 通用网页提取

**职责**：跨平台网页内容提取
**依赖**：yt-dlp

**文件位置**：[core/video_downloader.py](core/video_downloader.py)
Makefile 命令**：
```bash
make whoosh-rebuild                      # 重建索引
make whoosh-search Q="关键词"            # 测试搜索
```

**文件位置**：[db/whoosh_search.py](db/whoosh_search.py)

---

## 🖥️ 命令行接口

### cli/search_cli.py - 搜索 CLI

**职责**：命令行搜索、浏览、标签管理

| Makefile 命令 | 功能 |
|--------------|------|
| `make search Q="关键词"` | 全文搜索 |
| `make search-tags TAGS="标签1 标签2"` | 按标签搜索 |
| `make db-list [PAGE=1] [LIMIT=20]` | 列出视频（分页） |
| `make db-show ID=1` | 查看详情 |
| `make db-show ID=1 report` | 查看报告 |
| `make db-show ID=1 transcript` | 查看转写 |
| `make db-show ID=1 ocr` | 查看 OCR |
| `make db-tags` | 列出热门标签 |

**快捷别名**：
```bash
make s Q="..."                          # 相当于 search
make ls                                 # 相当于 db-list
make show id=1                          # 相当于 db-show
```
| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `load_browser_cookies()` | `domain: str` | `dict` | 从浏览器读取指定域名的 Cookie |
| `save_cookies()` | `domain: str, cookies: dict` | `bool` | 保存 Cookie 到本地 |
| `list_all_domains()` | - | `List[str]` | 列出所有已保存的 Cookie 域名 |

**支持平台**：知乎、小红书、Bilibili、Reddit、Twitter、通用网页

**文件位置**：[archiver/core/universal_archiver.py](archiver/core/universal_archiver.py)

---

### 🔍 db/repository.py - 数据库查询接口

**职责**：视频和网页记录的增删改查
### cli/main_cli.py - 主 CLI 入口

**职责**：统一的命令行界面

| 命令 | 说明 |
|------|------|
| `list` | 列出所有记录（支持分页） |
| `search` | 全文搜索 |
| `suggest` | AI 建议标签 |
| `stats` | 显示统计信息 |

**文件位置**：[cli/main_cli.py](cli/main_cli.py)

---

### cli/db_stats.py - 数据库统计

**职责**：显示库存统计信息

| Makefile 命令 | 功能 |
|--------------|------|
| `make db-stats` | 完整统计（视频 + 网页 + 存储） |
| `make db-stats-videos` | 仅视频统计 |
| `make db-stats-archives` | 仅网页统计 |
| `make db-stats-tags` | 标签统计 |

**文件位置**：[cli/db_stats.py](cli/db_stats.py)

---

## 🗄️ 数据库管理

### db/schema.py - 数据库初始化

**职责**：创建表、维护数据库版本

| Makefile 命令 | 功能 |
|--------------|------|
| `make db-init` | 初始化数据库 |
| `make db-reset` | 删除所有数据并重建 |
| `make db-status` | 检查数据库状态 |
| `make db-backup` | 备份数据库 |
| `make db-vacuum` | 优化数据库（VACUUM） |

**文件位置**：[db/schema.py](db/schema.py)

---

## 🤖 Telegram Bot 集成

### cli/tg_bot.py - Telegram Bot 服务

**职责**：通过 Telegram 远程调用 MemoryIndex 功能

| 命令 | 功能 |
|------|------|
| `/search 关键词` | 全文搜索 |
| `/archive 网址` | 归档网页 |
| `/video 链接` | 下载并处理视频 |
| `/status` | 查看统计信息 |
| `/help` | 显示帮助 |

**Makefile 命令**：
```bash
make tg-bot-setup                        # 配置 Bot Token
make tg-bot-start                        # 启动 Bot（终端常驻）
make tg-bot-stop                         # 停止 Bot
```

**配置文件**：`~/.memoryindex/.env`（TG_BOT_TOKEN、TG_ALLOWED_USER_ID）

**文件位置**：[cli/tg_bot.py](cli/tg_bot.py)

---

## ⚙️ 系统配置

### core/config.py - 全局配置

**职责**：环境变量、API 密钥、文件路径

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `GROQ_API_KEY` | str | Groq API（**必需**） |
| `GEMINI_API_KEY` | str | Gemini API（可选） |
| `TG_BOT_TOKEN` | str | Telegram Token（可选） |
| `GROQ_MODEL` | str | Groq 推理模型 |
| `DOCS_DIR` | Path | MD 输出目录 |
| `VIDEOS_DIR` | Path | 视频存储目录 |
| `DB_PATH` | Path | 数据库文件 |
| `OCR_ENGINE` | str | OCR 引擎（vision/paddle） |

**配置方式**：编辑 `.env` 文件或环境变量

**文件位置**：[core/config.py](core/config.py)

---

## 🚀 环境与工具

### 常用 Makefile Targets

#### 🔧 环境管理
```bash
make setup                               # 初始化环境（一次性）
make install                             # 安装依赖
make check                               # 检查环境配置
make clean                               # 清理输出文件
make install-chromium                    # 安装 Chromium
make install-paddle-ocr                  # 安装 PaddleOCR
```

#### 🔍 测试与调试
```bash
make test                                # 运行虚拟环境测试
make test-vision-ocr                     # 测试 Apple Vision OCR
make db-test                             # 测试数据库功能
make selftest                            # 全功能自检
```

---

## 📚 数据模型

### db/models.py - 数据类定义

```python
@dataclass
class Video:
    content_hash: str                    # MD5
    title: str                           # 标题
    source_type: SourceType              # local/youtube/bilibili
    file_path: str                       # 本地路径
    duration_seconds: Optional[float]
    transcript: Optional[str]            # 转写文本
    ocr_text: Optional[str]              # OCR 文本
    summary: Optional[str]               # AI 摘要
    tags: List[str]                      # 标签
    topics: List[str]                    # 主题
    created_at: datetime
    updated_at: datetime

@dataclass
class Archive:
    url: str                             # 源 URL
    title: str                           # 标题
    content: str                         # Markdown 内容
    source_type: SourceType              # zhihu/reddit/twitter/...
    metadata: Dict[str, Any]             # 平台特定数据
    tags: List[str]
    created_at: datetime
```

---

## 📍 快速查找表

| 我想做什么 | 使用 | 位置 |
|----------|------|------|
| 处理本地视频 | `make run Path=...` | [core/process_video.py](core/process_video.py) |
| 下载在线视频 | `make download URL=...` | [core/video_downloader.py](core/video_downloader.py) |
| 归档网页 | `make archive URL=...` | [core/archive_processor.py](core/archive_processor.py) |
| 登录（保存登录态） | `make login` | [scripts/login_helper.py](scripts/login_helper.py) |
| 全文搜索 | `make search Q="..."` | [cli/search_cli.py](cli/search_cli.py) |
| 清理 URL 追踪  | `make url-clean URL=...` | [scripts/url_cleaner.py](scripts/url_cleaner.py) |
| Telegram 控制 | `make tg-bot-setup` | [cli/tg_bot.py](cli/tg_bot.py) |
| 查看统计 | `make db-stats` | [cli/db_stats.py](cli/db_stats.py) |
| 重建索引 | `make whoosh-rebuild` | [db/whoosh_search.py](db/whoosh_search.py) |
| 备份数据 | `make db-backup` | [db/schema.py](db/schema.py) |

---

## 变更约定

- **新增模块/新增入口/变更参数**：必须同步更新本文件
- **本文件保持"索引风格"**：宁可少，但要准；不要长篇教程
- **函数超 100 行或参数 >5 个**：请在对应源文件补充 docstring
**支持域名**：xiaohongshu.com、zhihu.com、twitter.com、reddit.com、bilibili.com 等

**文件位置**：[scripts/cookie_manager.py](scripts/cookie_manager.py)

---

### 🔗 scripts/url_cleaner.py - URL 反追踪 & 短链接还原

**职责**：移除 URL 中的追踪参数和统计码，还原短链接

| 功能 | 说明 |
|------|------|
| 追踪参数移除 | 去除 `utm_*`, `fbclid`, `gclid` 等跟踪器 |
| 短链接还原 | 自动展开 `bit.ly`, `tinyurl`, `ow.ly` 等 |
| 文本提取 | 支持从分享文本自动提取 URL |

**文件位置**：[scripts/url_cleaner.py](scripts/url_cleaner.py)

---

### 🤖 cli/tg_bot.py - Telegram Bot 集成

**职责**：通过 Telegram 命令实时调用 MemoryIndex 功能

| 命令 | 功能 | 说明 |
|------|------|------|
| `/search 关键词` | 全文搜索 | 在知识库中搜索 |
| `/archive 链接` | 归档网页 | 实时归档网页到知识库 |
| `/video 链接` | 处理视频 | 下载并处理视频 |
| `/status` | 查看统计 | 显示数据库统计信息 |
| `/help` | 帮助 | 显示所有可用命令 |

**配置文件**：`~/.memoryindex/.env`

**文件位置**：[cli/tg_bot.py](cli/tg_bot.py)

---

### 📊 cli/main_cli.py - 主命令行界面

**职责**：统一的命令行入口，支持列表、搜索、查看、删除等操作

| 命令 | 功能 |
|------|------|
| `list` | 列表视图（带分页） |
| `search` | 全文搜索 |
| `suggest` | AI 建议标签 |
| `stats` | 数据库统计 |

**文件位置**：[cli/main_cli.py](cli/main_cli.py)
