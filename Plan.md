# MemoryIndex 项目规划

## 项目目标

建立基于 MIAP（MemoryIndex 智能代理协议）的个人知识管理系统，通过专门化 AI 代理自动将视频和网页内容转化为结构化知识库。

## 核心架构

### 1. 视频处理流程 - 完成

- [x] 视频下载（YouTube、Bilibili、小红书、抖音、本地文件）
- [x] 音频提取与转写（Groq Whisper）
- [x] 智能帧截取与 OCR（Apple Vision / PaddleOCR）
- [x] AI 摘要生成（Gemini / Groq LLM）
- [x] 时间轴与报告生成
- [x] 数据库存储标签与主题

### 2. 网页归档流程 - 完成

- [x] 平台检测与 Cookie 管理
- [x] 内容提取（知乎、小红书、Reddit、Twitter、Bilibili、WordPress）
- [x] HTML 转 Markdown（DrissionPage / Crawl4AI 双引擎）
- [x] 噪声过滤与清理
- [x] 4 阶段 AI 报告生成（快速摘要→详细分析→合并→展示摘要）
- [x] 数据库集成与搜索索引更新

### 3. 知识检索系统 - 完成

- [x] Whoosh 全文索引 + jieba 中文分词
- [x] 混合搜索策略（Whoosh → FTS5 → LIKE 回退）
- [x] 多字段搜索（标题、内容、转写文本、OCR）
- [x] 标签与主题过滤
- [x] 噪声标签自动过滤（tag_filters.py）

### 4. 系统集成 - 完成

- [x] 模块化设计（CLI/Core/DB/Archiver/Backend/Frontend）
- [x] Makefile 一键操作（19+ 命令）
- [x] 虚拟环境自动化
- [x] Telegram Bot 远程控制

### 5. Web 前后端系统 - 完成

- [x] FastAPI REST 后端（16 个 API 端点）
- [x] React 前端应用（5 个页面，7 个组件）
- [x] Zustand 状态管理 + TypeScript 类型安全
- [x] Tailwind CSS 响应式设计（Indigo 主题、毛玻璃导航栏）
- [x] 快速导入 + 异步任务进度轮询
- [x] 一键启动脚本（start-dev.sh）

### 6. 已完成的维护项

- [x] Web 列表摘要完整显示（2026-03-23）
- [x] Web 导入支持分享文本自动提取链接（2026-03-23）
- [x] 视频与网页处理升级为多阶段生成独立展示摘要 summary.md（2026-03-26）
- [x] 前端完整重新设计：现代化 UI（2026-03-26）
- [x] Dashboard 合并至首页（2026-03-26）
- [x] 噪声标签过滤（2026-03-26）
- [x] 修复归档 LLM 重命名后数据库路径不匹配问题（2026-03-27）
- [x] 前端快速导入增加网页/视频单选按钮（2026-03-27）
- [x] 小红书 Cookie 诊断（2026-03-27）
- [x] API.md / README.md / Plan.md / Remember.md 全面审查与重写（2026-03-27）
- [x] 修复 `/api/videos` 与 `/api/archives` 因 `sqlite3.Row.get` 导致的 500 错误（2026-03-27）

## 已知技术债务（超 1000 行文件）

| 文件 | 行数 | 建议拆分方向 |
|------|------|------------|
| `core/process_video.py` | 2173 | audio_processor / ocr_handler / llm_service / report_generator + 主协调器 |
| `archiver/core/drission_crawler.py` | 1798 | ocr_processor / cookie_handler / content_extractor |
| `core/archive_processor.py` | 1375 | archive_report_generator / archive_llm_service / archive_content_handler |
| `core/video_downloader.py` | 1235 | downloader_ytdlp / downloader_bbdown / downloader_xhs / screenshot_handler |
| `db/repository.py` | 1127 | video_repository / archive_repository / tag_repository / stats_repository |
| `db/search.py` | 1010 | search_builder + 核心搜索 |

## 代码审计发现（2026-03-27）

> 完整报告见 `Report/20260327_full_code_audit.md`

### 高严重度

- [x] **H-01** SearchRepository 导入源已替换为 search.py 的 Whoosh+FTS5 混合搜索（2026-03-27）
- [x] **H-03** 搜索结果 type 判定已补全 twitter/xiaohongshu（使用 WEB_SOURCES 常量）（2026-03-27）
- [x] **H-04** explicit_summary 重复子查询已删除（2026-03-30）
- [x] **H-05** 资料库「全部」分页已优化，移除错误的 halfOffset 逻辑（2026-03-30）
- [x] **H-06** 前端标签过滤改为服务端 SQL 过滤，修复分页后数据丢失（2026-03-30）
- [x] **H-07** 搜索页标签切换已在 store 层自动重置页码（2026-03-27）
- [x] **H-09** 前端任务 error 后已正确清理 taskId 停止轮询（2026-03-27）
- [x] **H-10** 前端导入错误信息已改用 err.response?.data?.detail（2026-03-27）

### 中严重度

- [x] **M-01** `_row_to_video()` 已改为复用传入 conn 查标签，避免嵌套连接（2026-03-30）
- [x] **M-02** `update_task()` 已修复为 `if status is not None:`（2026-03-27）
- [x] **M-03** `detect_url_type()` 已补全抖音/TikTok/小红书（2026-03-27）
- [x] **M-04** `web_sources` 已统一为 `WEB_SOURCES` 常量，全文件引用（2026-03-27）
- [x] **M-10** CORS 已改为具体开发域名（localhost:3000/5173）（2026-03-27）
- [x] **M-11** TaskManager 已添加 threading.Lock 保护（2026-03-30）
- [x] **M-12** `_is_valid_url()` 裸 except 已改为 `except (ValueError, AttributeError)`（2026-03-27）

### 已知技术债务（旧项保留）

- `backend/background_worker.py` 全为模拟实现
- `cli/db_stats.py` 中 `show_stats()` 死代码
- ~~`archiver/utils/url_parser.py` 默认返回 `wordpress` 而非 `generic`~~（已修复，当前返回 `generic`）

### 超 1000 行文件（拆分待定）

| 文件 | 行数 | 建议拆分方向 |
|------|------|------------|
| `core/process_video.py` | 2173 | audio_processor / ocr_handler / llm_service / report_generator + 主协调器 |
| `archiver/core/drission_crawler.py` | 1798 | ocr_processor / cookie_handler / content_extractor |
| `core/archive_processor.py` | 1375 | archive_report_generator / archive_llm_service / archive_content_handler |
| `core/video_downloader.py` | 1235 | downloader_ytdlp / downloader_bbdown / downloader_xhs / screenshot_handler |
| `db/repository.py` | 1127 | video_repository / archive_repository / tag_repository / stats_repository |
| `db/search.py` | 1010 | search_builder + 核心搜索 |

## 待办事项

### 短期修复（~~已全部完成~~）

- [x] 替换 SearchRepository 导入源（H-01）
- [x] 补全搜索 type 判定遗漏平台（H-03）
- [x] 修复前端任务轮询 + 错误信息（H-09 + H-10）
- [x] 修复搜索页标签不重置页码（H-07）
- [x] 统一 web_sources 常量定义（M-04）
- [x] 补全 detect_url_type 平台列表（M-03）
- [x] 删除重复 explicit_summary 子查询（H-04）
- [x] 优化资料库「全部」分页逻辑（H-05）

### 中期改进

- [x] 后端新增标签过滤 API（彻底解决 H-06 客户端标签过滤问题，2026-03-30）
- [x] `_row_to_video()` 嵌套连接优化（M-01，2026-03-30）
- [x] TaskManager 加锁保护（M-11，2026-03-30）
- [ ] 后台任务集成真实处理逻辑（替代 asyncio.sleep 模拟）
- [x] 清理死代码：删除重复 list_videos()、未使用的 StatsStore/TagStore/StatCard（2026-03-30）

### 长期规划

- [ ] 拆分超 1000 行文件（需求驱动，逐步进行）
- [ ] 新增数据源支持（需求驱动）
- [ ] 前端身份验证与权限管理
- [ ] Docker 容器化部署
- [ ] 单元测试覆盖

## 快速启动

```bash
make setup                    # 初始化环境
bash start-dev.sh             # 启动 Web 前后端
make run Path=video.mp4       # 处理视频
make archive URL=...          # 归档网页
make search Q="关键词"        # 全文搜索
```
