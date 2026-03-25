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
| `/api/import` | POST | 导入内容（支持 URL 或分享文本，自动提取链接）【新】 |
| `/api/health` | GET | 健康检查 |

**参数示例**：
```bash
# 搜索
curl "http://localhost:8000/api/search?q=ai&tags=技术&limit=20&offset=0"

# 获取第一个视频的详情
curl "http://localhost:8000/api/content/1?content_type=video"

# 获取统计
curl "http://localhost:8000/api/stats"

# 导入内容【新】
curl -X POST http://localhost:8000/api/import \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=test", "content_type": "auto", "use_ocr": true}'
```

#### POST /api/import - 导入内容【新】

**功能**：导入 URL（视频/网页），自动检测类型；支持直接粘贴分享文本并自动提取链接

**请求体**：
```json
{
  "url": "https://www.youtube.com/watch?v=abc123",
  "content_type": "auto",
  "use_ocr": true
}
```

**请求参数**：

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| url | string | - | URL 或包含 URL 的分享文本（必需，后端会自动提取） |
| content_type | string | auto | auto\|video\|archive |
| use_ocr | boolean | false | 是否启用 OCR 识别 |

**响应示例**（成功）：
```json
{
  "status": "queued",
  "content_id": null,
  "message": "已将 video 添加到处理队列，请稍候...",
  "content_type": "video"
}
```

**响应示例**（错误）：
```json
{
  "status": "error",
  "content_id": null,
  "message": "无效的 URL 格式",
  "content_type": null
}
```

**自动检测规则**：

| 域名 | 检测结果 |
|------|---------|
| youtube.com, youtu.be | video |
| bilibili.com, b23.tv | video |
| vimeo.com | video |
| qq.com/video, iqiyi.com | video |
| 其他所有 | archive |

**输入提取规则**：
- Web 导入与 CLI 复用同一套 URL 提取逻辑；
- 支持“纯 URL”与“分享文本（含多余描述）”两种输入；
- 无法提取有效链接时，接口返回错误提示。

**相关代码**：
- `backend/services.py`: `ImportService` 类
- `backend/models.py`: `ImportRequest`, `ImportResponse` 类
- `backend/main.py`: POST /api/import 端点

#### 任务管理 API（用于追踪导入进度）【新】

**功能**：查询后台任务的处理进度、状态、日志

##### GET /api/tasks/{task_id} - 查询任务状态【新】

**功能**：获取指定任务的详细信息和实时进度

**参数**：
- `task_id` (path）：任务 ID（由 POST /api/archive-run 返回）

**响应示例**（处理中）：
```json
{
  "task_id": "2565a5ba",
  "task_type": "archive",
  "status": "processing",
  "url": "https://x.com/test",
  "use_ocr": false,
  "progress": 45,
  "current_step": "🔍 正在解析网页内容",
  "created_at": "2026-03-19T10:00:00",
  "started_at": "2026-03-19T10:00:02",
  "completed_at": null,
  "logs": [
    {
      "timestamp": "2026-03-19T10:00:00",
      "level": "info",
      "message": "🔄 开始处理: archive (https://x.com/test)"
    },
    {
      "timestamp": "2026-03-19T10:00:02",
      "level": "info",
      "message": "📥 正在下载网页..."
    }
  ]
}
```

**响应示例**（已完成）：
```json
{
  "task_id": "2565a5ba",
  "status": "completed",
  "progress": 100,
  "current_step": "✅ 任务完成",
  "completed_at": "2026-03-19T10:00:15",
  "result": {
    "url": "https://x.com/test",
    "type": "archive",
    "status": "saved"
  }
}
```

**状态值**：
- `pending`: 等待处理
- `processing`: 正在处理
- `completed`: 已完成
- `error`: 处理失败
- `cancelled`: 已取消

**进度百分比**：
- 0%: 初始化
- 20-40%: 下载/解析
- 50-80%: 识别/分析
- 90-100%: 保存/完成

##### GET /api/tasks/stats - 获取任务统计【新】

**功能**：获取所有任务的统计信息

**响应示例**：
```json
{
  "total": 10,
  "pending": 1,
  "processing": 0,
  "completed": 8,
  "error": 1
}
```

**相关代码**：
- `backend/task_manager.py`: Task, TaskManager 类
- `backend/background_worker.py`: BackgroundTaskWorker 类
- `backend/models.py`: TaskStatusResponse 类
- `backend/main.py`: GET /api/tasks/{task_id}, GET /api/tasks/stats 端点
- `frontend/src/pages/HomePage.tsx`: 任务进度显示组件

---

### frontend/ - React Web 应用

**职责**：现代化 Web 界面，支持搜索、浏览、导入、内容展示

| 页面 | URL | 功能 |
|------|-----|------|
| 首页 | `/` | 知识库概览、统计指标、快速导入（含任务进度）、最近内容、热门标签 |
| 资料库 | `/archives` | 全部/视频/网页切换、网格卡片布局、标签筛选、排序、分页 |
| 搜索 | `/search` | 全文搜索、侧栏标签过滤、分页 |
| 详情 | `/content/{id}` | 完整内容（摘要/README/转写/OCR/报告选项卡） |
| 统计 | `/dashboard` | 自动重定向到首页（已合并） |

**技术栈**：React 18 + TypeScript + Tailwind CSS + Zustand + Axios

**设计风格**：Indigo 主色调、毛玻璃导航栏、卡片式网格布局、自定义 CSS 组件类（glass-nav / card / badge / tag-pill / btn-primary 等）、响应式移动端支持

**核心文件**：
- `src/api/client.ts` - API 请求客户端
- `src/components/Layout.tsx` - 全局布局（毛玻璃导航栏 + 响应式移动菜单）
- `src/components/` - UI 组件（SearchBar / ContentPreview / ContentCard / Pagination / TagFilter）
- `src/pages/` - 页面组件
- `src/store/` - Zustand 状态管理
- `src/index.css` - 全局样式（自定义组件类、prose 排版、滚动条）

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
