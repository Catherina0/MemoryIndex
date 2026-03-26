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

## 已知技术债务（超 1000 行文件）

| 文件 | 行数 | 建议拆分方向 |
|------|------|------------|
| `core/process_video.py` | 2173 | audio_processor / ocr_handler / llm_service / report_generator + 主协调器 |
| `archiver/core/drission_crawler.py` | 1798 | ocr_processor / cookie_handler / content_extractor |
| `core/archive_processor.py` | 1375 | archive_report_generator / archive_llm_service / archive_content_handler |
| `core/video_downloader.py` | 1235 | downloader_ytdlp / downloader_bbdown / downloader_xhs / screenshot_handler |
| `db/repository.py` | 1127 | video_repository / archive_repository / tag_repository / stats_repository |
| `db/search.py` | 1010 | search_builder + 核心搜索 |

## 已知代码问题

- `db/repository.py` 中 `SearchRepository` 与 `db/search.py` 中 `SearchRepository` 类名冲突
- `db/repository.py` 中 `list_videos()` 定义了两次（行 225 和 527）
- `backend/background_worker.py` 任务处理为模拟实现，未集成真实逻辑
- `cli/db_stats.py` 中 `show_stats()` 函数为死代码
- `frontend/src/store/index.ts` 中 StatsStore 和 TagStore 未被使用
- 根目录散落测试文件（已被 .gitignore 忽略）

## 待办事项

- [ ] 拆分超 1000 行文件（需求驱动，逐步进行）
- [ ] 后台任务集成真实处理逻辑（替代 asyncio.sleep 模拟）
- [ ] 新增数据源支持（需求驱动）
- [ ] 性能优化（数据库查询、搜索速度）
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
