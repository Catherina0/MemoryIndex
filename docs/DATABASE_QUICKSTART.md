# 数据库与搜索系统 - 快速开始

## 一、快速部署（5分钟上手）

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装新增依赖
pip install tabulate
```

### 2. 初始化数据库

```bash
# 创建数据库（自动创建所有表和索引）
python -m db.schema

# 验证创建成功
python -m db.schema --check
```

输出示例：
```
✅ 数据库初始化成功: storage/database/knowledge.db
📊 已创建 9 张表: artifacts, embeddings, fts_content, ...
🔍 全文搜索表: fts_content, fts_content_config, ...

📊 数据库统计:
  videos: 0
  artifacts: 0
  tags: 4
  topics: 0
  timeline_entries: 0
  fts_content: 0
  db_size_mb: 0.12 MB
```

### 3. 运行测试

```bash
# 测试所有功能（创建测试数据）
python test_database.py
```

### 4. 测试搜索

```bash
# 搜索测试数据
python search_cli.py search "机器学习"

# 按标签搜索
python search_cli.py tags --tags 机器学习 深度学习 --match-all

# 查看热门标签
python search_cli.py list-tags
```

---

## 二、集成到现有流程

### 方法1：最小改动（推荐）

在 `process_video.py` 末尾添加数据库保存逻辑：

```python
# 在 process_video.py 末尾添加

from db_integration import VideoProcessor

def main():
    # ... 原有处理逻辑 ...
    
    # 处理完成后，保存到数据库
    try:
        processor = VideoProcessor()
        db_video_id = processor.process_and_save(
            video_path=str(video_path),
            output_dir=output_dir,
            source_url=args.url if hasattr(args, 'url') else None,
            source_type='bilibili' if 'bilibili' in str(video_path) else 'local',
            video_id=extract_video_id(video_path),  # 从文件名提取
            processing_config={
                'fps': fps,
                'asr_model': 'whisper-large-v3',
                'ocr_model': 'paddleocr'
            }
        )
        
        print(f"\n✅ 已保存到数据库: video_id={db_video_id}")
        print(f"🔍 搜索命令: python search_cli.py search \"关键词\"")
        
    except Exception as e:
        print(f"⚠️  保存数据库失败（不影响处理结果）: {e}")
```

### 方法2：完全重构

用 `VideoProcessor` 替换原有处理逻辑：

```python
from db_integration import VideoProcessor

def main():
    args = parse_args()
    
    processor = VideoProcessor()
    video_id = processor.process_and_save(
        video_path=args.video,
        output_dir=Path(args.output),
        source_url=args.url,
        source_type=args.source_type,
        video_id=args.video_id
    )
    
    print(f"✅ 处理完成: video_id={video_id}")
```

---

## 三、实际使用场景

### 场景1：处理视频并搜索

```bash
# 1. 处理视频（自动入库）
python process_video.py --video video.mp4

# 2. 搜索内容
python search_cli.py search "关键词"

# 3. 按标签查找
python search_cli.py tags --tags 教育 科技
```

### 场景2：批量导入历史视频

```python
# batch_import.py
from pathlib import Path
from db_integration import VideoProcessor

processor = VideoProcessor()
output_base = Path('./output')

# 遍历已处理的视频
for video_dir in output_base.glob('*/'):
    if not video_dir.is_dir():
        continue
    
    # 读取已有的处理结果
    report_file = video_dir / 'report.md'
    transcript_file = video_dir / 'transcript_raw.json'
    
    if report_file.exists():
        # 构造视频信息并入库
        # TODO: 从文件名解析元信息
        print(f"导入: {video_dir.name}")
```

### 场景3：搜索并跳转到视频时间点

```python
from db import SearchRepository

repo = SearchRepository()

# 搜索
results = repo.search(query="神经网络", fields='transcript')

for result in results:
    print(f"视频: {result.video_title}")
    print(f"时间点: {result.timestamp_seconds}s")
    print(f"文件: {result.file_path}")
    
    # 构造跳转命令
    if result.timestamp_seconds:
        cmd = f"ffplay -ss {result.timestamp_seconds} {result.file_path}"
        print(f"播放命令: {cmd}")
```

---

## 四、常用命令速查

### 数据库管理

```bash
# 初始化数据库
python -m db.schema

# 重建数据库（删除所有数据）
python -m db.schema --force

# 检查数据库状态
python -m db.schema --check

# SQLite 命令行（调试用）
sqlite3 storage/database/knowledge.db
```

### 搜索命令

```bash
# 全文搜索（所有字段）
python search_cli.py search "机器学习"

# 仅在转写中搜索
python search_cli.py search "人工智能" --field transcript

# 仅在报告中搜索
python search_cli.py search "深度学习" --field report

# 按标签过滤（AND逻辑）
python search_cli.py search "神经网络" --tags 教育 科技

# 按时间排序（最新优先）
python search_cli.py search "CNN" --sort date --limit 10

# 按相关性排序（默认）
python search_cli.py search "RNN" --sort relevance

# JSON 输出（用于脚本）
python search_cli.py search "LSTM" --json

# 详细输出（包含完整信息）
python search_cli.py search "transformer" -v
```

### 标签操作

```bash
# 按标签搜索（包含所有标签）
python search_cli.py tags --tags 机器学习 深度学习 --match-all

# 按标签搜索（包含任一标签）
python search_cli.py tags --tags 教育 娱乐

# 列出热门标签
python search_cli.py list-tags --limit 30

# 标签自动补全
python search_cli.py suggest "机器"
```

### 主题搜索

```bash
# 搜索主题
python search_cli.py topics "卷积神经网络"

# JSON 输出
python search_cli.py topics "LSTM" --json
```

---

## 五、数据库查询（SQL）

直接使用 SQLite 命令行：

```bash
sqlite3 storage/database/knowledge.db
```

### 常用查询

```sql
-- 查看所有视频
SELECT id, title, source_type, duration_seconds, status 
FROM videos 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看视频的标签
SELECT v.title, GROUP_CONCAT(t.name, ', ') as tags
FROM videos v
LEFT JOIN video_tags vt ON v.id = vt.video_id
LEFT JOIN tags t ON vt.tag_id = t.id
GROUP BY v.id;

-- 全文搜索
SELECT 
    v.title,
    fts.source_field,
    snippet(fts_content, 3, '**', '**', '...', 30) as snippet,
    fts.rank
FROM fts_content fts
JOIN videos v ON fts.video_id = v.id
WHERE fts.content MATCH '机器学习'
ORDER BY fts.rank
LIMIT 10;

-- 查看热门标签
SELECT name, count, 
       (SELECT COUNT(*) FROM video_tags WHERE tag_id = tags.id) as video_count
FROM tags
ORDER BY count DESC
LIMIT 20;

-- 查看视频的主题
SELECT title, summary, start_time, end_time
FROM topics
WHERE video_id = 1
ORDER BY sequence;

-- 查看处理统计
SELECT 
    source_type,
    COUNT(*) as count,
    SUM(duration_seconds) / 60 as total_minutes
FROM videos
GROUP BY source_type;
```

---

## 六、性能优化技巧

### 1. 定期维护

```bash
# 每处理 1000 个视频后执行
sqlite3 storage/database/knowledge.db "VACUUM;"
```

### 2. 备份数据库

```bash
# 备份
cp storage/database/knowledge.db storage/database/knowledge_backup_$(date +%Y%m%d).db

# 或使用 SQLite 备份命令
sqlite3 storage/database/knowledge.db ".backup storage/database/backup.db"
```

### 3. 导出数据

```python
# export_data.py
from db import VideoRepository
import json

repo = VideoRepository()
videos = repo.list_videos(limit=10000)

# 导出为 JSON
with open('export.json', 'w', encoding='utf-8') as f:
    json.dump([v.to_dict() for v in videos], f, ensure_ascii=False, indent=2)
```

---

## 七、故障排查

### 问题1：数据库锁定

```bash
# 关闭所有连接
sqlite3 storage/database/knowledge.db "PRAGMA wal_checkpoint;"
```

### 问题2：搜索无结果

```python
# 检查 FTS 索引
from db import VideoRepository

repo = VideoRepository()

# 重建所有视频的索引
for video in repo.list_videos(limit=1000):
    repo.update_fts_index(video.id)
    print(f"重建索引: {video.id} - {video.title}")
```

### 问题3：查看日志

```sql
-- 查看处理日志
SELECT * FROM processing_logs 
WHERE status = 'failed' 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## 八、下一步

### 扩展功能

1. **添加 Web UI**：使用 FastAPI + Vue.js
2. **向量检索**：集成 OpenAI Embeddings
3. **文档入库**：支持 PDF、网页
4. **自动标签**：使用 LLM 自动提取标签
5. **相似推荐**：基于内容的视频推荐

### 学习资源

- SQLite FTS5 文档: https://www.sqlite.org/fts5.html
- Repository Pattern: https://martinfowler.com/eaaCatalog/repository.html
- 数据库设计详细文档: [DATABASE_DESIGN.md](./DATABASE_DESIGN.md)

---

## 附录：完整示例代码

### 示例1：完整处理流程

```python
#!/usr/bin/env python3
"""
完整的视频处理 + 数据库存储示例
"""
from pathlib import Path
from db_integration import VideoProcessor

def process_video_example():
    # 初始化处理器
    processor = VideoProcessor()
    
    # 处理视频
    video_id = processor.process_and_save(
        video_path='./videos/test.mp4',
        output_dir=Path('./output/test'),
        source_url='https://example.com/video',
        source_type='local',
        processing_config={'fps': 1}
    )
    
    print(f"✅ 处理完成: video_id={video_id}")
    
    # 搜索刚处理的视频
    from db import SearchRepository
    
    search = SearchRepository()
    results = search.search(query="关键词")
    
    for result in results:
        print(f"找到: {result.video_title}")

if __name__ == '__main__':
    process_video_example()
```

### 示例2：批量搜索

```python
#!/usr/bin/env python3
"""
批量搜索并导出结果
"""
from db import SearchRepository
import json

def batch_search():
    repo = SearchRepository()
    
    # 多个关键词搜索
    keywords = ['机器学习', '深度学习', '神经网络', 'CNN', 'RNN']
    
    all_results = {}
    for keyword in keywords:
        results = repo.search(query=keyword, limit=10)
        all_results[keyword] = [r.to_dict() for r in results]
        print(f"'{keyword}': 找到 {len(results)} 个结果")
    
    # 导出结果
    with open('search_results.json', 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("✅ 结果已导出到 search_results.json")

if __name__ == '__main__':
    batch_search()
```

---

**🎉 现在你已经掌握了完整的数据库与搜索系统！**

有问题？查看 [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) 获取更多细节。
