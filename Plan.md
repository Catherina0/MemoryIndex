# MemoryIndex 项目规划

## 项目目标
建立基于 MIAP（MemoryIndex 智能代理协议）的个人知识管理系统，通过专门化 AI 代理自动将视频和网页内容转化为结构化知识库。

## 核心架构

### 1. 视频处理流程 ✅ 完成
- [x] 视频下载（YouTube、Bilibili、本地文件）
- [x] 音频提取与转写（Groq Whisper）
- [x] 智能帧截取与 OCR（Apple Vision / PaddleOCR）
- [x] AI 摘要生成（Gemini / Groq LLM）
- [x] 时间轴与报告生成
- [x] 数据库存储标签与主题

### 2. 网页归档流程 ✅ 完成
- [x] 平台检测与 Cookie 管理
- [x] 内容提取（知乎、小红书、Reddit、Twitter、Bilibili）
- [x] HTML 转 Markdown
- [x] 噪声过滤与清理
- [x] 数据库集成

### 3. 知识检索系统 ✅ 完成
- [x] Whoosh 全文索引
- [x] jieba 中文分词
- [x] 多字段搜索（标题、内容、转写文本、OCR）
- [x] 标签与主题过滤

### 4. 系统集成 ✅ 完成
- [x] 模块化设计（CLI/Core/DB/Archiver）
- [x] 单一职责原则（每个模块 <1000 行）
- [x] Makefile 一键操作
- [x] 虚拟环境自动化

### 5. Web 前后端系统 ✅ 完成（2026-03-18）
- [x] FastAPI REST 后端（7 个 API 端点）
- [x] React 前端应用（4 个页面，7 个组件）
- [x] Zustand 状态管理
- [x] Tailwind CSS 响应式设计
- [x] TypeScript 类型安全
- [x] 一键启动脚本（start-dev.sh）
- [x] 完整文档与快速指南

### 6. 持续维护
- [ ] 新增数据源支持（需求驱动）
- [ ] 性能优化（数据库查询、搜索速度）
- [ ] 前端身份验证与权限管理
- [ ] 分布式存储支持（可选）
- [ ] Docker 容器化部署
- [ ] 单元测试与 E2E 测试（可选）

## 当前状态
**主要功能完整可用**，覆盖视频处理、网页归档、全文搜索、数据管理。文档完善，模块清晰，可投入日常使用。

## 快速启动（参考 Makefile）
```bash
make setup                    # 初始化环境
make run Path=video.mp4       # 处理视频（音频模式）
make ocr Path=video.mp4       # 处理视频（完整 OCR 模式）
make archive URL=...          # 归档网页
make search Q="关键词"        # 全文搜索
```