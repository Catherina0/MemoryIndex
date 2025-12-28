# 数据库与搜索系统设计文档

## 系统架构

### 技术栈
- **数据库**: SQLite 3.x
- **全文搜索**: FTS5 (Full-Text Search)
- **ORM**: 无（使用原生 SQL + Repository Pattern）
- **分词**: FTS5 内置 unicode61 + porter tokenizer

### 目录结构
```
knowledge/
├── db/
│   ├── __init__.py          # 模块入口
│   ├── schema.sql           # 数据库 Schema（9张表）
│   ├── schema.py            # 数据库初始化
│   ├── models.py            # 数据模型（dataclass）
│   ├── repository.py        # 数据访问层（CRUD）
│   └── search.py            # 搜索 API
├── storage/
│   ├── database/
│   │   └── knowledge.db     # SQLite 数据库文件
│   ├── videos/              # 原视频存储（按hash命名）
│   └── artifacts/           # 处理产物
│       └── {video_hash}/
│           ├── frames/
│           ├── audio.wav
│           ├── transcript.json
│           ├── ocr.json
│           └── report.md
├── db_integration.py        # 集成到 process_video.py
└── search_cli.py           # 搜索命令行工具
```

---

## 数据库 Schema

### 核心表

#### 1. videos（视频元信息）
```sql
- id: 主键
- content_hash: SHA256 hash（唯一，去重）
- video_id: 平台视频ID（如 BV1xxx）
- source_type: 来源类型（local/youtube/bilibili等）
- source_url: 原始URL
- title: 标准化标题
- duration_seconds: 时长
- file_path: 视频文件路径
- status: 处理状态（pending/processing/completed/failed）
- created_at, processed_at, updated_at
```

#### 2. artifacts（处理产物）
```sql
- id: 主键
- video_id: 外键 → videos
- artifact_type: 类型（transcript/ocr/report）
- content_text: 纯文本内容
- content_json: 结构化内容（JSON）
- model_name: 使用的模型
- char_count, word_count: 统计信息
```

#### 3. tags（标签）
```sql
- id: 主键
- name: 标签名（唯一，忽略大小写）
- category: 分类（topic/person/event等）
- count: 使用次数
```

#### 4. video_tags（视频-标签关联）
```sql
- video_id: 外键 → videos
- tag_id: 外键 → tags
- source: auto/manual
- confidence: 置信度（0-1）
```

#### 5. topics（主题/章节）
```sql
- id: 主键
- video_id: 外键 → videos
- title: 主题标题
- summary: 摘要
- start_time, end_time: 时间范围
- keywords: 关键词（JSON数组）
- sequence: 顺序
```

#### 6. timeline_entries（时间线）
```sql
- id: 主键
- video_id: 外键 → videos
- timestamp_seconds: 时间点
- frame_number: 帧号
- transcript_text: 转写文本
- ocr_text: OCR文本
- frame_path: 帧图片路径
```

#### 7. fts_content（全文搜索虚拟表）
```sql
CREATE VIRTUAL TABLE fts_content USING fts5(
    video_id UNINDEXED,
    source_field UNINDEXED,
    title,      -- 标题（高权重）
    content,    -- 内容
    tags        -- 标签
);
```

#### 8. embeddings（向量表，预留）
```sql
- id: 主键
- video_id: 外键 → videos
- embedding_blob: 向量数据（BLOB）
- embedding_model: 模型名称
- text_snippet: 对应文本
```

#### 9. processing_logs（处理日志）
```sql
- id: 主键
- video_id: 外键 → videos
- step_name: 步骤名称
- status: started/completed/failed
- duration_seconds: 耗时
```

---

## 数据写入流程

### 完整处理流程

```python
from db_integration import VideoProcessor

processor = VideoProcessor()

# 1. 开始处理（自动创建 video 记录）
video_id = processor.process_and_save(
    video_path='/path/to/video.mp4',
    output_dir=Path('./output/test_video'),
    source_url='https://bilibili.com/video/BV1xxx',
    source_type='bilibili',
    video_id='BV1xxx',
    processing_config={'fps': 1, 'model': 'whisper-large-v3'}
)
```

### 事务处理策略

1. **视频去重**：
   - 计算 `content_hash`（SHA256）
   - 查询 `videos` 表，如果存在则跳过

2. **状态管理**：
   - 创建记录时设为 `processing`
   - 处理完成后更新为 `completed`
   - 失败时更新为 `failed`（记录错误信息）

3. **批量插入**：
   - 时间线条目、主题等使用批量插入
   - 每个视频一个事务，确保原子性

4. **索引更新**：
   - 所有产物保存完成后，调用 `update_fts_index()`
   - 一次性将 report/transcript/ocr 写入 FTS 表

### 文件存储策略

**方案1：按 hash 存储（推荐）**
```
storage/
├── videos/
│   └── a1b2c3d4e5f6...mp4      # 按 content_hash 命名
└── artifacts/
    └── a1b2c3d4e5f6/
        ├── frames/
        │   ├── frame_00001.png
        │   └── ...
        ├── audio.wav
        ├── transcript.json
        ├── ocr.json
        └── report.md
```

优点：
- 自动去重
- 文件名稳定
- 便于引用

**方案2：按视频ID存储**
```
storage/
└── artifacts/
    └── bilibili_BV1xxx/
        └── ...
```

优点：
- 语义化
- 便于人工查找

---

## 搜索 API 设计

### Python API

```python
from db import SearchRepository
from db.search import SearchField, SortBy

repo = SearchRepository()

# 1. 全文搜索
results = repo.search(
    query="机器学习 深度学习",           # 搜索关键词
    tags=["教育", "科技"],               # 标签过滤（AND）
    fields=SearchField.ALL,              # 搜索范围
    limit=20,                            # 返回数量
    offset=0,                            # 分页
    sort_by=SortBy.RELEVANCE,           # 排序方式
    min_relevance=0.3                    # 最小相关性
)

for result in results:
    print(f"{result.video_title}")
    print(f"  来源: {result.source_field}")
    print(f"  片段: {result.matched_snippet}")
    print(f"  时间: {result.timestamp_seconds}s")
    print(f"  标签: {', '.join(result.tags)}")
    print(f"  相关性: {result.relevance_score}")

# 2. 按标签搜索
videos = repo.search_by_tags(
    tags=["机器学习", "深度学习"],
    match_all=True    # True=AND, False=OR
)

# 3. 搜索主题
topics = repo.search_topics(query="神经网络")

# 4. 热门标签
tags = repo.get_popular_tags(limit=50)

# 5. 标签自动补全
suggestions = repo.suggest_tags(prefix="机器")
```

### SearchResult 数据结构

```python
@dataclass
class SearchResult:
    video_id: int                        # 视频ID
    video_title: str                     # 视频标题
    source_field: str                    # 来源字段（report/transcript/ocr/topic）
    
    matched_snippet: str                 # 匹配片段（带上下文）
    full_content: Optional[str]          # 完整内容（可选）
    
    timestamp_seconds: Optional[float]   # 时间点
    timestamp_range: Optional[tuple]     # 时间范围 (start, end)
    
    tags: List[str]                      # 标签列表
    source_type: str                     # 来源类型
    duration_seconds: float              # 视频时长
    file_path: str                       # 文件路径
    
    rank: float                          # BM25 排名
    relevance_score: float               # 相关性分数（0-1）
    created_at: datetime
```

---

## 命令行工具使用

### 初始化数据库

```bash
# 创建数据库
python -m db.schema

# 强制重建（删除所有数据）
python -m db.schema --force

# 检查健康状态
python -m db.schema --check
```

### 搜索命令

```bash
# 全文搜索
python search_cli.py search "机器学习"

# 在转写中搜索
python search_cli.py search "人工智能" --field transcript

# 按标签过滤
python search_cli.py search "深度学习" --tags 教育 科技

# 按时间排序
python search_cli.py search "神经网络" --sort date --limit 10

# JSON 输出
python search_cli.py search "LSTM" --json

# 按标签搜索（AND逻辑）
python search_cli.py tags --tags 机器学习 深度学习 --match-all

# 搜索主题
python search_cli.py topics "卷积神经网络"

# 列出热门标签
python search_cli.py list-tags --limit 30

# 标签自动补全
python search_cli.py suggest "机器"
```

---

## SQL 查询示例

### 1. 搜索包含关键词的视频

```sql
-- 使用 FTS5 搜索
SELECT 
    v.id,
    v.title,
    fts.source_field,
    snippet(fts_content, 3, '<b>', '</b>', '...', 30) as snippet,
    fts.rank
FROM fts_content fts
JOIN videos v ON fts.video_id = v.id
WHERE fts.content MATCH '机器学习 OR 深度学习'
ORDER BY fts.rank
LIMIT 20;
```

### 2. 按标签搜索（包含所有标签）

```sql
SELECT 
    v.*,
    GROUP_CONCAT(t.name, ', ') as tags
FROM videos v
JOIN video_tags vt ON v.id = vt.video_id
JOIN tags t ON vt.tag_id = t.id
WHERE v.id IN (
    SELECT vt2.video_id FROM video_tags vt2
    JOIN tags t2 ON vt2.tag_id = t2.id
    WHERE t2.name IN ('教育', '科技')
    GROUP BY vt2.video_id
    HAVING COUNT(DISTINCT t2.id) = 2
)
GROUP BY v.id;
```

### 3. 获取视频的完整信息

```sql
-- 使用视图
SELECT * FROM v_videos_full WHERE id = 123;
```

### 4. 搜索主题

```sql
SELECT 
    t.*,
    v.title as video_title
FROM topics t
JOIN videos v ON t.video_id = v.id
WHERE t.title LIKE '%神经网络%'
   OR t.summary LIKE '%神经网络%'
ORDER BY t.video_id, t.sequence;
```

---

## 性能优化建议

### 索引策略

已创建的索引：
- `videos.content_hash` (UNIQUE)
- `videos.source_type, video_id`
- `videos.status`
- `videos.created_at`
- `artifacts.video_id, artifact_type`
- `topics.video_id, sequence`
- `timeline_entries.video_id, timestamp_seconds`
- FTS5 自动索引

### 查询优化

1. **使用视图**：常用查询封装为视图
2. **分页查询**：使用 LIMIT + OFFSET
3. **预计算**：标签使用次数冗余存储
4. **批量操作**：时间线/主题批量插入

### 扩展性建议

数据量达到以下规模时考虑优化：
- **< 1000个视频**：SQLite + FTS5 足够
- **1000-10000**：启用 WAL 模式，定期 VACUUM
- **10000-100000**：考虑分表（按年份/来源）
- **> 100000**：考虑迁移到 PostgreSQL + pg_trgm

---

## 未来扩展路线

### 1. 向量检索（Embeddings）

**表结构已预留**：
```sql
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    video_id INTEGER,
    embedding_blob BLOB,      -- 存储向量
    embedding_model TEXT,     -- 模型名称
    text_snippet TEXT,        -- 对应文本
    ...
);
```

**实现方案**：
- 使用 OpenAI `text-embedding-3-small` 或本地模型
- 每个产物分块（500-1000 tokens）
- 使用 `faiss-cpu` 或 `hnswlib` 构建向量索引
- 混合检索：BM25 + 向量相似度

**示例代码**：
```python
# 生成 embedding
from openai import OpenAI

client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text_chunk
)
embedding = response.data[0].embedding

# 保存到数据库
conn.execute("""
    INSERT INTO embeddings (video_id, embedding_blob, text_snippet)
    VALUES (?, ?, ?)
""", (video_id, pickle.dumps(embedding), text_chunk))

# 查询时使用 faiss
import faiss
import numpy as np

# 构建索引
embeddings_matrix = np.array([...])
index = faiss.IndexFlatL2(768)  # 维度
index.add(embeddings_matrix)

# 搜索
query_embedding = get_embedding(query)
D, I = index.search(query_embedding, k=10)
```

### 2. 支持文档入库

**扩展 source_type**：
```python
class SourceType(str, Enum):
    LOCAL = 'local'
    YOUTUBE = 'youtube'
    BILIBILI = 'bilibili'
    # 新增
    PDF = 'pdf'
    WEBPAGE = 'webpage'
    MARKDOWN = 'markdown'
```

**artifact_type 扩展**：
```python
class ArtifactType(str, Enum):
    TRANSCRIPT = 'transcript'
    OCR = 'ocr'
    REPORT = 'report'
    # 新增
    EXTRACTED_TEXT = 'extracted_text'  # PDF提取文本
    PARSED_HTML = 'parsed_html'        # 网页内容
```

**处理流程**：
```python
# PDF 处理
def process_pdf(pdf_path: str) -> int:
    # 1. 计算 hash
    content_hash = calculate_hash(pdf_path)
    
    # 2. 创建视频记录（复用 videos 表）
    video = Video(
        content_hash=content_hash,
        source_type=SourceType.PDF,
        title=pdf_path.stem,
        file_path=pdf_path,
        ...
    )
    video_id = repo.create_video(video)
    
    # 3. 提取文本（PyPDF2/pdfplumber）
    text = extract_pdf_text(pdf_path)
    
    # 4. 保存产物
    artifact = Artifact(
        video_id=video_id,
        artifact_type=ArtifactType.EXTRACTED_TEXT,
        content_text=text,
        ...
    )
    repo.save_artifact(artifact)
    
    # 5. LLM 生成摘要
    report = generate_report(text)
    
    # 6. 更新 FTS 索引
    repo.update_fts_index(video_id)
    
    return video_id
```

### 3. Web UI

使用 **FastAPI** + **Vue.js** 构建 Web 界面：

```python
# api.py
from fastapi import FastAPI, Query
from typing import List, Optional

app = FastAPI()

@app.get("/api/search")
async def search(
    q: str,
    tags: Optional[List[str]] = Query(None),
    field: str = "all",
    limit: int = 20
):
    repo = SearchRepository()
    results = repo.search(q, tags=tags, fields=field, limit=limit)
    return {"results": [r.to_dict() for r in results]}

@app.get("/api/video/{video_id}")
async def get_video(video_id: int):
    repo = VideoRepository()
    video = repo.get_video_by_id(video_id)
    return video.to_dict()

@app.get("/api/tags")
async def get_tags():
    repo = SearchRepository()
    return repo.get_popular_tags()
```

---

## 附录：依赖安装

```bash
# 基础依赖
pip install python-dotenv

# 搜索工具依赖
pip install tabulate

# Web API（可选）
pip install fastapi uvicorn

# 向量检索（可选）
pip install openai faiss-cpu numpy

# 文档处理（可选）
pip install PyPDF2 pdfplumber beautifulsoup4
```

---

## 总结

这套系统提供了：

✅ **完整的数据库设计**（9张表 + FTS5）  
✅ **Repository 模式**（解耦业务逻辑）  
✅ **强大的搜索功能**（全文/标签/主题/向量）  
✅ **命令行工具**（开箱即用）  
✅ **扩展路线**（文档入库、向量检索、Web UI）  
✅ **性能优化**（索引、批量操作、分页）  

**最小可行实现（MVP）**：
1. 初始化数据库：`python -m db.schema`
2. 集成到 `process_video.py`：导入 `VideoProcessor`
3. 搜索测试：`python search_cli.py search "关键词"`

立即可用，无需额外配置！
