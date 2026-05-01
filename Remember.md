# MemoryIndex - 核心信息速查

## 项目一句话

**基于 MIAP 代理协议的个人知识管理系统** + **现代化前后端 Web 应用**——用 AI 自动将互联网内容（视频、网页）转化为结构化可搜索的知识库。

## 快速启动

```bash
bash start-dev.sh                           # 一键启动前后端（前端 :3000 / 后端 :8000）
make run Path=~/Downloads/video.mp4         # 处理视频（音频模式）
make ocr Path=~/Downloads/video.mp4         # 处理视频（完整 OCR）
make archive URL=https://zhihu.com/...      # 归档网页
make search Q="关键词"                       # 全文搜索
make db-stats                               # 查看统计
make login                                  # 保存浏览器 Cookie
```

## 环境配置

必需：`.env` 文件中的 `GROQ_API_KEY`（音频转写）
可选：`GEMINI_API_KEY`（摘要）、`TG_BOT_TOKEN` + `TG_ALLOWED_USER_ID`（Telegram Bot）

## 关键路径

| 内容 | 位置 |
|------|------|
| 数据库 | `storage/database/knowledge.db` |
| 搜索索引 | `storage/whoosh_index/` |
| 配置 | `core/config.py` + `.env` |
| 后端入口 | `backend/main.py` |
| 前端入口 | `frontend/src/App.tsx` |
| 浏览器数据 | `browser_data/` |

## 已知限制

- macOS 优先：Vision OCR 原生支持；其他系统需 PaddleOCR
- 6 个文件超 1000 行限制（详见 Plan.md 技术债务表）
- 前端 `/api/*` 出现 500 → 优先检查 8000 端口后端是否启动
- 后台任务进度跳跃式更新（下载/处理期间无中间进度），属设计限制

## 文档导航

| 文档 | 用途 |
|------|------|
| API.md | 模块索引与接口速查 |
| CLAUDE.md | 协作规范 |
| Plan.md | 项目规划与技术债务 |
| MANUAL.md | 使用手册 |
| Docs/ | 详细开发文档 |
