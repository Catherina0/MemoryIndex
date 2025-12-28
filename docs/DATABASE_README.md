# 数据库与搜索功能（新增）

## 概述

为视频处理系统添加了完整的数据库存储和搜索能力，支持：

- ✅ **数据持久化**：视频元信息、转写、OCR、报告全部入库
- ✅ **智能搜索**：全文搜索（FTS5）、标签搜索、主题搜索
- ✅ **自动去重**：基于文件 hash 的智能去重
- ✅ **时间戳定位**：搜索结果直接关联到视频时间点
- ✅ **命令行工具**：开箱即用的搜索命令

## 快速开始

### 1. 初始化数据库

```bash
# 创建数据库（自动创建所有表和索引）
python -m db.schema

# 验证
python -m db.schema --check
```

### 2. 处理视频（自动入库）

处理视频时，结果会自动保存到数据库：

```bash
# 处理本地视频
python process_video.py --video video.mp4

# 处理完成后，数据自动入库
```

### 3. 搜索视频内容

```bash
# 全文搜索
python search_cli.py search "机器学习"

# 在转写中搜索
python search_cli.py search "深度学习" --field transcript

# 按标签搜索
python search_cli.py tags --tags 教育 科技 --match-all

# 查看热门标签
python search_cli.py list-tags

# 搜索主题
python search_cli.py topics "神经网络"
```

## 主要功能

### 1. 数据存储

**存储内容：**
- 视频元信息（来源、平台、时长、文件路径等）
- ASR 转写全文（带时间戳的 segments）
- OCR 识别文本（带帧号和时间戳）
- LLM 生成的 Markdown 报告
- 自动提取的标签
- 主题总结和章节划分
- 完整时间线（音画对齐）

**数据库结构：**
```
SQLite (storage/database/knowledge.db)
├── videos (视频)
├── artifacts (转写/OCR/报告)
├── tags (标签)
├── topics (主题/章节)
├── timeline_entries (时间线)
└── fts_content (全文搜索索引)
```

### 2. 搜索功能

#### 全文搜索

支持在所有文本内容中搜索：

```python
from db import SearchRepository

repo = SearchRepository()
results = repo.search(
    query="机器学习 深度学习",
    tags=["教育"],           # 标签过滤
    fields='transcript',     # 搜索范围
    sort_by='relevance'      # 排序方式
)

for result in results:
    print(f"视频: {result.video_title}")
    print(f"片段: {result.matched_snippet}")
    print(f"时间: {result.timestamp_seconds}s")
    print(f"相关性: {result.relevance_score}")
```

#### 搜索结果包含

- ✅ **匹配片段**：带上下文的匹配文本
- ✅ **时间戳**：精确到秒的时间点
- ✅ **来源字段**：标注来自报告/转写/OCR
- ✅ **相关性分数**：BM25 算法计算的相关度
- ✅ **标签列表**：视频的所有标签
- ✅ **视频路径**：可直接播放

#### 标签搜索

```bash
# 查找包含所有标签的视频（AND逻辑）
python search_cli.py tags --tags 机器学习 深度学习 --match-all

# 查找包含任一标签的视频（OR逻辑）
python search_cli.py tags --tags 教育 娱乐
```

#### 主题搜索

```bash
# 在主题和章节中搜索
python search_cli.py topics "卷积神经网络"
```

### 3. 去重机制

使用 SHA256 hash 自动去重：

```python
# 自动计算文件 hash
content_hash = repo.calculate_content_hash(video_path)

# 检查是否已存在
existing = repo.get_video_by_hash(content_hash)
if existing:
    print(f"视频已存在，跳过处理")
```

### 4. 状态管理

每个视频都有处理状态：

- `pending` - 等待处理
- `processing` - 处理中
- `completed` - 处理完成
- `failed` - 处理失败

```python
# 更新状态
repo.update_video_status(video_id, ProcessingStatus.COMPLETED)
```

## 数据库架构

### 核心表

1. **videos** - 视频元信息
   - content_hash (唯一标识)
   - title, source_type, source_url
   - duration_seconds, file_path
   - status, created_at

2. **artifacts** - 处理产物
   - video_id (外键)
   - artifact_type (transcript/ocr/report)
   - content_text (纯文本)
   - content_json (结构化数据)

3. **tags** - 标签
   - name (唯一)
   - category, count

4. **topics** - 主题/章节
   - video_id (外键)
   - title, summary
   - start_time, end_time
   - keywords, key_points

5. **timeline_entries** - 时间线
   - video_id (外键)
   - timestamp_seconds
   - transcript_text, ocr_text
   - frame_path

6. **fts_content** - 全文搜索（FTS5）
   - video_id, source_field
   - title, content, tags

### 性能特点

- ✅ SQLite + FTS5 全文搜索
- ✅ BM25 相关性排名
- ✅ 完整的事务支持
- ✅ 自动维护的索引
- ✅ 查询性能：< 100ms（1000个视频以内）

## 命令行工具

### 搜索命令

```bash
# 全文搜索
search "关键词"                          # 基础搜索
search "关键词" --field transcript       # 仅搜索转写
search "关键词" --field report          # 仅搜索报告
search "关键词" --tags 教育 科技         # 标签过滤
search "关键词" --sort date             # 按时间排序
search "关键词" --json                  # JSON输出
search "关键词" -v                      # 详细输出

# 标签操作
tags --tags 标签1 标签2 --match-all     # 包含所有标签
tags --tags 标签1 标签2                 # 包含任一标签
list-tags --limit 50                    # 热门标签
suggest "前缀"                          # 标签自动补全

# 主题搜索
topics "主题关键词"                     # 搜索主题
```

### 数据库管理

```bash
# 初始化
python -m db.schema

# 重建（删除所有数据）
python -m db.schema --force

# 检查状态
python -m db.schema --check

# 运行测试
python test_database.py
```

## Python API

### 基础使用

```python
from db import VideoRepository, SearchRepository
from db.models import Video, SourceType

# 创建视频记录
repo = VideoRepository()
video = Video(
    content_hash="abc123...",
    title="测试视频",
    source_type=SourceType.LOCAL,
    file_path="/path/to/video.mp4"
)
video_id = repo.create_video(video)

# 搜索
search_repo = SearchRepository()
results = search_repo.search(query="关键词")
```

### 完整处理流程

```python
from db_integration import VideoProcessor

processor = VideoProcessor()
video_id = processor.process_and_save(
    video_path='video.mp4',
    output_dir=Path('./output/video_001'),
    source_url='https://example.com/video',
    source_type='local'
)
```

## 文档

详细文档请查看：

- **[DATABASE_DESIGN.md](./docs/DATABASE_DESIGN.md)** - 完整设计文档
  - 架构设计与技术选型
  - 数据库 Schema 详解
  - 搜索 API 文档
  - SQL 查询示例
  - 性能优化建议

- **[DATABASE_QUICKSTART.md](./docs/DATABASE_QUICKSTART.md)** - 快速开始
  - 5分钟部署指南
  - 集成到现有系统
  - 常用命令速查
  - 故障排查

- **[DATABASE_SUMMARY.md](./docs/DATABASE_SUMMARY.md)** - 实施总结
  - 功能清单
  - 技术决策
  - 扩展路线

## 测试

运行完整测试套件：

```bash
python test_database.py
```

测试覆盖：
- ✅ 数据库初始化
- ✅ 视频 CRUD 操作
- ✅ 产物保存（转写/OCR/报告）
- ✅ 标签管理
- ✅ 主题保存
- ✅ 时间线构建
- ✅ 全文搜索索引
- ✅ 搜索功能（全文/标签/主题）

## 文件结构

```
knowledge/
├── db/                          # 数据库模块
│   ├── __init__.py
│   ├── schema.sql              # 数据库定义
│   ├── schema.py               # 初始化和连接
│   ├── models.py               # 数据模型
│   ├── repository.py           # 数据访问层
│   └── search.py               # 搜索API
├── storage/                     # 数据存储
│   ├── database/
│   │   └── knowledge.db        # SQLite数据库
│   ├── videos/                 # 视频文件
│   └── artifacts/              # 处理产物
├── db_integration.py           # 集成适配器
├── search_cli.py              # 命令行工具
├── test_database.py           # 功能测试
└── docs/
    ├── DATABASE_DESIGN.md
    ├── DATABASE_QUICKSTART.md
    └── DATABASE_SUMMARY.md
```

## 依赖

新增依赖：

```txt
tabulate>=0.9.0    # 命令行表格输出
```

安装：

```bash
pip install tabulate
```

## 性能

### 适用规模

| 视频数量 | 查询性能 | 建议 |
|---------|---------|------|
| < 1,000 | < 100ms | 直接使用 |
| 1,000 - 10,000 | < 200ms | 定期维护 |
| > 10,000 | < 500ms | 考虑优化 |

### 优化建议

- 定期执行 `VACUUM`
- 使用批量操作
- 合理使用分页

## 未来扩展

### 1. 向量检索

已预留 `embeddings` 表，可添加：

- 语义搜索（vs 关键词匹配）
- 相似视频推荐
- RAG 问答系统

### 2. 文档入库

复用现有架构，支持：

- PDF 文档
- 网页内容
- Markdown 文档

### 3. Web UI

使用 FastAPI + Vue.js 构建 Web 界面。

---

**立即开始：**

```bash
# 1. 初始化
python -m db.schema

# 2. 测试
python test_database.py

# 3. 搜索
python search_cli.py search "测试"
```

更多信息请查看 [详细文档](./docs/DATABASE_DESIGN.md)。
