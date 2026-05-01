# MemoryIndex - API 索引与接口摘要

> 优先查看此文件定位模块和入口。**按功能分类**，快速定位所有模块与命令。

---

## Web 前后端系统

### backend/main.py - FastAPI 服务

**职责**：REST API 服务入口（469 行）

| 端点 | 方法 | 功能 | 关键参数 |
|------|------|------|---------|
| `/` | GET | API 根路径检查 | - |
| `/api/search` | GET | 全文搜索 | q, tags, source_type, limit, offset |
| `/api/videos` | GET | 视频列表 | limit, offset, sort, tags（逗号分隔） |
| `/api/archives` | GET | 网页列表 | limit, offset, sort, tags（逗号分隔） |
| `/api/content/{id}` | GET | 内容详情 | content_type=video/archive |
| `/api/content/{id}/media` | GET | 视频流媒体 | - |
| `/api/tags` | GET | 标签列表（自动过滤噪声标签） | limit |
| `/api/stats` | GET | 统计信息 | - |
| `/api/import` | POST | 导入内容（URL 或分享文本） | url, content_type, use_ocr |
| `/api/download-run` | POST | 下载视频（快速） | url |
| `/api/download-ocr` | POST | 下载视频（+OCR） | url |
| `/api/archive-run` | POST | 归档网页（快速） | url |
| `/api/archive-ocr` | POST | 归档网页（+OCR） | url |
| `/api/tasks/{task_id}` | GET | 查询任务状态 | - |
| `/api/tasks/stats` | GET | 任务统计 | - |
| `/api/health` | GET | 健康检查 | - |

**CORS**：允许 localhost:3000/5173 开发域名
**依赖注入**：通过 Repository → Service 分层

---

### backend/services.py - 业务逻辑层

**职责**：搜索、内容、统计、导入 4 个服务类（520 行）

| 服务 | 关键方法 | 说明 |
|------|---------|------|
| `SearchService` | `search(query, tags, source_type, limit, offset)` | 全文搜索 |
| `ContentService` | `list_videos(limit, offset, sort, tags)`, `list_archives(limit, offset, sort, tags)`, `get_video_detail()`, `get_archive_detail()` | 内容管理 |
| `StatsService` | `get_statistics()`, `get_all_tags(limit)` | 统计与标签 |
| `ImportService` | `import_content(url, content_type, use_ocr)`, `detect_url_type(url)` | 导入与类型检测 |

**URL 类型自动检测规则**：youtube/bilibili/vimeo → video，其他 → archive

---

### backend/models.py - 数据模型

**职责**：Pydantic 请求/响应模型（252 行）

关键模型：`ImportRequest`、`ImportResponse`、`SearchResultItem`、`VideoDetailResponse`、`StatsResponse`、`TaskStatusResponse`

---

### backend/task_manager.py - 任务管理

**职责**：后台任务创建、状态追踪、清理（220 行）

| API | 说明 |
|-----|------|
| `TaskManager.create_task(task_type, url, use_ocr)` | 创建任务，返回 task_id |
| `TaskManager.update_task(task_id, status, progress, current_step)` | 更新进度 |
| `TaskManager.complete_task(task_id, result)` | 标记完成 |
| `TaskManager.get_statistics()` | 返回 pending/processing/completed/error 计数 |

**状态值**：pending → processing → completed/error/cancelled

---

### backend/background_worker.py - 后台处理

**职责**：异步执行归档/下载任务（真实实现，约 200 行）

| 方法 | 说明 |
|------|------|
| `process_archive_task(task_id, url, use_ocr)` | 调用 `archive_and_save()`（core/archive_processor.py），完整归档流程 |
| `process_video_task(task_id, url, use_ocr)` | 先 `VideoDownloader.download_video()`，再 `process_video()`，均用 `run_in_executor` 包裹 |

**进度节点**：

- 归档：5% 初始化 → 10% 下载 → 98% 完成
- 视频：5% 初始化 → 10% 下载 → 40% 下载完 → 45% 处理 → 98% 完成

---

### frontend/ - React Web 应用

**职责**：现代化 Web 界面（2468 行总计）

| 页面 | URL | 功能 |
|------|-----|------|
| 首页 | `/` | 统计、快速导入（含任务进度轮询）、最近内容、热门标签 |
| 资料库 | `/archives` | 全部/视频/网页切换、标签筛选、排序、分页 |
| 搜索 | `/search` | 全文搜索、侧栏标签过滤、分页 |
| 详情 | `/content/{id}` | Markdown 渲染、多标签页（摘要/README/转写/OCR/报告） |
| Dashboard | `/dashboard` | 重定向到首页 |

**技术栈**：React 18 + TypeScript + Tailwind CSS + Zustand + Axios + Vite
**设计风格**：Indigo 主色调、毛玻璃导航栏、卡片网格布局

**核心文件**：
- `src/api/client.ts` - API 请求客户端（180 行）
- `src/store/index.ts` - Zustand 状态管理（77 行）
- `src/components/` - 7 个 UI 组件
- `src/pages/` - 5 个页面组件

---

## 视频处理模块

### core/process_video.py - 核心视频处理

**职责**：视频转写、OCR、AI 摘要、报告生成、数据库存储（2173 行 - 超限）

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `process_video()` | `video_path, output_dir, with_frames, ocr_lang, source_url, ...` | `None` | 完整 15 步处理流程 |
| `transcribe_audio_with_groq()` | `audio_path: Path` | `dict{text, segments}` | Groq Whisper 转写 |
| `summarize_with_gemini()` | `full_text, custom_prompt` | `tuple[str, str]` | Gemini LLM 摘要 |
| `summarize_with_gpt_oss_120b()` | `full_text` | `tuple[str, str]` | Groq OSS 模型 |
| `generate_detailed_content()` | `full_text` | `tuple[str, int]` | 结构化详细内容 |
| `generate_display_summary()` | `full_text` | `str` | 展示用摘要 |
| `generate_formatted_report()` | `full_text, timeline, output_path` | `str` | Markdown 报告 |
| `save_to_database()` | `title, content_hash, file_path, ...` | `int\|None` | 存储到数据库 |
| `extract_frames()` | `video_path, frames_dir` | `None` | 视频抽帧 |

**处理流程**：创建目录 → 提取音频 → 转录 → 抽帧 → OCR → 时间轴匹配 → LLM 摘要 → 报告 → 数据库

**依赖**：ffmpeg, Groq API, Google Gemini API, OCR 引擎

**Makefile**：`make run Path=...`（音频模式）、`make ocr Path=...`（完整模式）

---

### core/video_downloader.py - 视频下载器

**职责**：多平台视频下载（1235 行 - 超限）

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `VideoDownloader.download_video()` | `url, force_redownload` | `LocalFileInfo` | 下载视频 |
| `VideoDownloader._detect_platform()` | `url` | `str` | 平台检测 |
| `VideoDownloader.check_already_downloaded()` | `url` | `dict\|None` | DB 去重检查 |
| `extract_url_from_text()` | `text` | `str\|None` | 从文本提取 URL |

**支持平台**：YouTube, Bilibili, 小红书, 抖音, TikTok, Twitter
**降级策略**：yt-dlp → BBDown(B站) / XHS-Downloader(小红书)
**依赖**：yt-dlp, BBDown, DrissionPage

**Makefile**：`make download URL=...`、`make download-run URL=...`、`make download-ocr URL=...`

---

### core/archive_processor.py - 网页归档 LLM 处理

**职责**：网页内容的 AI 报告生成与数据库存储（1375 行 - 超限）

| API | 参数 | 返回 | 说明 |
|-----|------|------|------|
| `ArchiveProcessor.process_and_save()` | `url, output_dir, archive_result, source_type, with_ocr` | `int` | 15 步处理入口 |
| `ArchiveProcessor._generate_report_for_archive()` | `archived_content, output_dir, with_ocr` | `dict` | 4 阶段报告生成 |
| `ArchiveProcessor._generate_display_summary()` | `report_text` | `str` | 展示摘要 |

**4 阶段 AI 报告**：快速摘要 → 详细分析 → 合并 → 展示摘要
**长文本处理**：>100k tokens 自动分段

---

### core/smart_frame_extractor.py - 智能抽帧

**职责**：基于状态机的视频关键帧提取（321 行）

| API | 说明 |
|-----|------|
| `SmartFrameExtractor.extract(video_path, output_dir, temp_dir)` | 主抽帧流程 |

**特点**：Grid-Max 变化检测、STABLE/TRANSITION 状态机、智能融合

---

### core/config.py - 全局配置

**职责**：单例配置管理器（140 行）

主要配置项：`GROQ_API_KEY`（必需）、`GEMINI_API_KEY`、`TG_BOT_TOKEN`、`OCR_ENGINE`、`DB_PATH`

---

### core/process_media.py - 媒体分发器

**职责**：根据文件类型分发到对应处理器（188 行）

支持：`.txt`, `.md`, `.png`, `.jpg`, `.mp4`, `.mkv`, `.mp3` 等

---

### core/image_utils.py - 图片工具

**职责**：超长图片分割（71 行）

| API | 说明 |
|-----|------|
| `split_long_image(image_path, max_height, overlap)` | 按高度分割图片 |

---

## 网页归档模块

### archiver/core/crawler.py - Crawl4AI 归档器

**职责**：基于 Crawl4AI 的网页归档（831 行）

| API | 说明 |
|-----|------|
| `UniversalArchiver.archive(url, platform_adapter, cookies, mode, ...)` | 异步归档单 URL |
| `UniversalArchiver.archive_batch(urls, max_concurrent)` | 批量异步归档 |

**特点**：优先尝试 DrissionPage，失败回退 Crawl4AI

---

### archiver/core/drission_crawler.py - DrissionPage 归档器

**职责**：基于 DrissionPage 的网页归档（1798 行 - 超限）

| API | 说明 |
|-----|------|
| `DrissionArchiver.archive(url, platform_adapter, mode, ...)` | 同步归档 |
| `DrissionArchiver.capture_screenshot(url, output_path)` | 网页截图 |

**特点**：反爬对抗、登录状态检测、多平台 Cookie 加载

---

### archiver/core/markdown_converter.py - Markdown 转换

**职责**：HTML → Markdown（153 行）

| API | 说明 |
|-----|------|
| `MarkdownConverter.convert(html, title, url, platform, ...)` | 转换并生成 frontmatter |

---

### archiver/platforms/ - 平台适配器

**职责**：7 个平台的 CSS 选择器与提取策略

| 平台 | 文件 | 特点 |
|------|------|------|
| 知乎 | zhihu.py | 正文选择器、评论排除 |
| 小红书 | xiaohongshu.py | 需要登录 |
| B站 | bilibili.py | 视频描述提取 |
| Reddit | reddit.py | 新旧两种布局 |
| Twitter/X | twitter.py | 推文/长文/详情多选择器 |
| WordPress | wordpress.py | 通用博客 |
| 基类 | base.py | PlatformConfig + PlatformAdapter |

---

### archiver/utils/ - 归档工具

| 模块 | 职责 | 关键 API |
|------|------|---------|
| `cookie_manager.py` (221行) | Cookie 管理 | `CookieManager.load_from_browser(domain)` |
| `url_parser.py` (151行) | URL 解析 | `detect_platform(url)`, `extract_url_from_text(text)` |
| `image_downloader.py` (496行) | 图片下载 | `ImageDownloader.download_all(urls)` |
| `browser_manager.py` (389行) | 浏览器单例 | `get_browser_manager()`, `new_tab()`, `close_tab()` |

---

## 数据库模块

### db/models.py - 数据模型

**职责**：数据类定义（247 行）

核心模型：`Video`、`Artifact`、`Tag`、`Topic`、`TimelineEntry`、`SearchResult`
枚举：`SourceType`(9种)、`ProcessingStatus`(4种)、`ArtifactType`(4种)

---

### db/repository.py - 数据访问层

**职责**：5 个仓库类的 CRUD 操作（1127 行 - 超限）

| 仓库类 | 关键方法 |
|--------|---------|
| `VideoRepository` | `create_video()`, `get_video_by_id/hash/source_url()`, `save_artifact()`, `save_tags()`, `list_videos_with_summary()`, `update_fts_index()` |
| `ArchiveRepository` | `list_archives()`, `get_archive_by_id()` |
| `TagRepository` | `get_all_tags()`, `get_popular_tags()` |
| `SearchRepository` | 基础搜索（完整版在 search.py） |
| `StatsRepository` | `get_stats()`, `get_storage_info()` |

> 注意：`SearchRepository` 在 repository.py 和 search.py 中都有定义，search.py 为完整版

---

### db/search.py - 全文搜索

**职责**：混合搜索引擎（1010 行 - 超限）

| API | 说明 |
|-----|------|
| `SearchRepository.search(query, tags, limit, offset, ...)` | 多关键词全文搜索 |
| `SearchRepository.search_by_tags(tags, limit)` | 按标签搜索 |
| `SearchRepository.get_popular_tags(limit)` | 热门标签 |

**搜索策略**：中文 → Whoosh+jieba 优先；英文 → FTS5+通配符变体；失败 → LIKE 回退

---

### db/tag_filters.py - 标签过滤

**职责**：过滤噪声标签（68 行）

| API | 说明 |
|-----|------|
| `filter_display_tags(tag_names)` | 过滤并去重 |
| `split_display_tags(tag_string)` | 解析 DB 聚合标签 |
| `get_hidden_tag_sql(column_name)` | SQL 过滤条件 |

**隐藏标签**：`标签`、`---`、`详细内容概括`、`详细内容概括完整版`、`OCR`

---

### db/whoosh_search.py - Whoosh 索引

**职责**：Whoosh + jieba 中文全文搜索（577 行）

| API | 说明 |
|-----|------|
| `WhooshSearchIndex.search(query, limit)` | 执行搜索 |
| `WhooshSearchIndex.rebuild_from_sqlite()` | 从 SQLite 重建索引 |
| `get_whoosh_index()` | 全局单例 |

---

### db/schema.py - 数据库初始化

**职责**：创建表、索引、触发器（320 行）

| API | 说明 |
|-----|------|
| `get_connection()` | 获取 SQLite 连接（WAL 模式） |
| `init_database()` | 从 schema.sql 创建表 |
| `check_database_health()` | 健康检查 |

**数据库路径**：`storage/database/knowledge.db`

---

## CLI 模块

### cli/main_cli.py - 主入口

**职责**：统一命令行界面、智能 URL 路由（439 行）

支持 19 个子命令：`init`, `search`, `tags`, `list`, `show`, `delete`, `process`, `download`, `archive`, `stats`, `config` 等

**智能路由**：自动识别 URL 类型 → 插入对应子命令

---

### cli/search_cli.py - 搜索 CLI

**职责**：命令行搜索、浏览、标签管理（650 行）

| Makefile 命令 | 功能 |
|--------------|------|
| `make search Q="关键词"` | 全文搜索 |
| `make search-tags TAGS="标签1 标签2"` | 按标签搜索 |
| `make db-list [PAGE=1]` | 列出内容 |
| `make db-show ID=1 [report/transcript/ocr]` | 查看详情 |

---

### cli/archive_cli.py - 归档 CLI

**职责**：网页归档命令行入口（268 行）

| Makefile 命令 | 功能 |
|--------------|------|
| `make archive URL=...` | 单个归档 |
| `make archive-run URL=...` | 归档 + AI 报告 |
| `make archive-batch FILE=urls.txt` | 批量归档 |

---

### cli/db_stats.py - 数据库统计

**职责**：显示库存统计信息（341 行）

| API | 说明 |
|-----|------|
| `get_archive_stats()` | 网页归档统计 |
| `get_video_stats()` | 视频文件统计 |
| `get_tag_stats()` | 标签使用统计 |

**Makefile**：`make db-stats`

---

### cli/tg_bot.py - Telegram Bot

**职责**：通过 Telegram 远程控制（385 行）

| 命令 | 功能 |
|------|------|
| `/search 关键词` | 全文搜索 |
| `/archive_run 链接` | 归档网页 |
| `/download_run 链接` | 下载视频 |
| `/db_stats` | 统计信息 |
| `/make <args>` | 动态执行 make 命令 |

**配置**：`TG_BOT_TOKEN`, `TG_ALLOWED_USER_ID`

---

## 脚本工具

### scripts/url_cleaner.py - URL 反追踪

**职责**：移除追踪参数、还原短链接（216 行）

| API | 说明 |
|-----|------|
| `clean_url(raw)` | 主入口：提取 → 展开短链 → 移除追踪器 |
| `remove_trackers(url)` | 移除 utm_* 等参数 |
| `resolve_short_url(url)` | 还原 bit.ly 等短链 |

**Makefile**：`make url-clean URL="..."`

---

### scripts/cookie_manager.py - Cookie 管理

**职责**：DrissionPage Cookie 操作（99 行）

**Makefile**：`make login`、`make list-cookies`、`make delete-cookie DOMAIN=...`

---

### scripts/login_helper.py - 登录助手

**职责**：交互式浏览器登录（208 行）

支持平台：知乎、小红书、B站、推特

---

## 快速查找表

| 我想做什么 | 使用 | 位置 |
|----------|------|------|
| 处理本地视频 | `make run Path=...` | core/process_video.py |
| 下载在线视频 | `make download URL=...` | core/video_downloader.py |
| 归档网页 | `make archive URL=...` | core/archive_processor.py |
| 登录保存 Cookie | `make login` | scripts/login_helper.py |
| 全文搜索 | `make search Q="..."` | cli/search_cli.py |
| 清理 URL 追踪 | `make url-clean URL=...` | scripts/url_cleaner.py |
| Telegram 控制 | `make tg-bot-start` | cli/tg_bot.py |
| 查看统计 | `make db-stats` | cli/db_stats.py |
| 重建索引 | `make whoosh-rebuild` | db/whoosh_search.py |
| 启动 Web | `bash start-dev.sh` | backend/main.py + frontend/ |

---

## 变更约定

- **新增模块/新增入口/变更参数**：必须同步更新本文件
- **本文件保持"索引风格"**：宁可少，但要准；不要长篇教程
