# 📦 视频处理自动入库功能

## 🎯 功能说明

从 2025-12-24 起，所有视频处理命令（`make run`、`make ocr` 等）完成后会**自动将结果保存到数据库**，无需手动操作。

## 💾 自动保存的内容

### 1. 视频基本信息
- 视频标题、来源、时长
- 文件路径、文件大小
- 内容哈希（用于去重）
- 处理状态和配置

### 2. 处理产物
- **语音转写** (transcript)：Groq Whisper 识别的文本 + 时间戳
- **OCR识别** (ocr)：PaddleOCR 识别的画面文字
- **AI报告** (report)：GPT-OSS 120B 生成的总结报告

### 3. 智能提取
- **标签** (tags)：从报告中自动提取关键词（最多10个）
- **主题章节** (topics)：识别章节标题和时间范围（最多20个）
- **时间线** (timeline)：逐秒的音画对照（OCR模式）

### 4. 搜索索引
- 全文搜索索引自动更新
- 支持在转写、OCR、报告中搜索关键词

## 🚀 使用流程

### 处理视频并自动入库

```bash
# 音频模式（快速）
make run VIDEO=/path/to/video.mp4

# OCR模式（完整）
make ocr VIDEO=/path/to/video.mp4

# 从URL下载并处理
make download-run URL="https://www.bilibili.com/video/BVxxxxx"
```

**处理完成后会看到：**
```
💾 保存到数据库...
   ✅ 创建视频记录 (ID: 1)
   ✅ 保存语音转写 (1234 字符)
   ✅ 保存OCR识别 (567 字符)
   ✅ 保存AI报告 (890 字符)
   ✅ 保存标签: 机器学习, 深度学习, 神经网络
   ✅ 保存主题: 3 个章节
   ✅ 保存时间线: 50 个条目
   🔍 更新全文搜索索引...
   ✅ 数据库保存完成！(视频ID: 1)
   💡 可以使用 `make search Q="关键词"` 来搜索
```

### 查看已处理的视频

```bash
# 列出所有视频（名称+标签+摘要）
make db-list

# 列出前50条
make db-list LIMIT=50

# 快捷命令
make ls
```

**输出示例：**
```
📹 视频列表 (共 5 条):

+-----+------+--------------------+----------+--------+-------------------+---------------------------+
|   # |   ID | 标题               | 来源     | 时长   | 标签              | 摘要                      |
+=====+======+====================+==========+========+===================+===========================+
|   1 |    5 | 机器学习入门教程   | bilibili | 15:30  | 教育, 机器学习    | 本视频介绍了机器学习...   |
+-----+------+--------------------+----------+--------+-------------------+---------------------------+
```

### 搜索已处理的内容

```bash
# 全文搜索
make search Q="神经网络"

# 按标签搜索
make search-tags TAGS="教育 科技"

# 查看热门标签
make db-tags

# 搜索主题章节
make search-topics Q="卷积神经网络"
```

## 🏷️ 标签自动提取

AI 会从总结报告中自动提取标签，支持以下格式：

```markdown
标签：机器学习、深度学习、神经网络
Tags: machine learning, deep learning
关键词：AI, 人工智能, 教育
Keywords: tutorial, beginner
```

提取规则：
- 自动识别多种分隔符（逗号、顿号、空格）
- 去重并过滤（长度 2-20 字符）
- 最多保留 10 个标签

## 📚 主题章节提取

AI 会从报告中提取章节结构：

```markdown
## 神经网络基础 [00:00 - 05:30]
介绍神经网络的基本概念...

## 卷积神经网络 [05:30 - 12:00]
讲解CNN的工作原理...
```

提取规则：
- 识别 `##` 开头的章节标题
- 提取时间范围（如果有）
- 收集章节描述（前200字符）
- 最多保留 20 个主题

## 🔍 全文搜索

所有产物自动索引到 FTS5 全文搜索引擎：

```bash
# 搜索所有内容
make search Q="机器学习"

# 仅搜索转写
make search Q="深度学习" FLAGS="--field transcript"

# 仅搜索OCR
make search Q="代码示例" FLAGS="--field ocr"

# 仅搜索报告
make search Q="总结" FLAGS="--field report"
```

## ⚙️ 去重机制

系统会计算视频文件的 SHA256 哈希值：
- 相同视频不会重复入库
- 检测到重复时会更新产物
- 不同处理模式（audio/OCR）可以补充产物

```
⚠️  视频已存在 (ID: 3)，更新产物...
✅ 保存OCR识别 (567 字符)  # 补充之前缺少的OCR
```

## 📊 数据库查看

```bash
# 查看统计信息
make db-status

# 查看所有视频
make db-list

# 查看热门标签
make db-tags
```

**输出示例：**
```
📊 数据库统计:
  videos: 12
  artifacts: 28
  tags: 45
  topics: 18
  timeline_entries: 350
  fts_content: 56
  db_size_mb: 2.5 MB
```

## 🛠️ 高级用法

### Python API 直接访问

```python
from db import VideoRepository, SearchRepository

# 查询视频
repo = VideoRepository()
videos = repo.list_videos(limit=10)

# 全文搜索
search_repo = SearchRepository()
results = search_repo.search("机器学习", limit=10)

# 按标签搜索
videos = search_repo.search_by_tags(["教育", "科技"], match_all=True)
```

### 手动添加标签

```python
from db import VideoRepository

repo = VideoRepository()
repo.save_tags(
    video_id=1,
    tag_names=["重要", "收藏"],
    source='manual',
    confidence=1.0
)
```

## 📝 注意事项

1. **首次使用需初始化数据库**
   ```bash
   make db-init
   ```

2. **标签和主题依赖AI总结质量**
   - 确保 Groq API Key 已配置
   - AI 总结越详细，提取的标签和主题越准确

3. **时间线仅在OCR模式下生成**
   - `make ocr` 会生成完整时间线
   - `make run` 只有语音转写，无时间线

4. **数据库文件位置**
   ```
   storage/database/knowledge.db
   ```
   - 可以备份此文件
   - 支持导出为 SQL

## 🔗 相关文档

- [数据库命令参考](DATABASE_COMMANDS.md)
- [搜索功能文档](../CHEATSHEET.txt)
- [快速开始](QUICKSTART.md)
