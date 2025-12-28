# 多关键词和模糊搜索功能

## 功能概述

搜索系统现在支持：
1. **多关键词搜索**（空格分隔）
2. **模糊搜索**（部分匹配）
3. **智能相似度计算**（多关键词共同参与评分）

## 使用方法

### 1. 单关键词搜索
```bash
make search Q="美国"
```
- 精确匹配"美国"
- 返回包含该词的所有视频

### 2. 多关键词搜索（OR逻辑）
```bash
make search Q="爱 intp"
```
- 返回包含"爱"**或**"intp"的视频
- 默认行为：匹配任一关键词即可
- **相似度计算**：
  ```python
  综合分数 = 平均相关性 * (0.7 + 0.3 * 覆盖率)
  覆盖率 = 匹配关键词数 / 总关键词数
  ```
- 同时匹配多个关键词的视频会获得更高分数

**示例结果**：
- ID=8包含"intp"和"爱"：相关性0.96 ✨
- ID=13只包含"intp"：相关性0.79
- ID=7只包含"intp"：相关性0.78

### 3. 多关键词搜索（AND逻辑）
```bash
make search Q="爱 intp" FLAGS="--match-all"
```
- 返回**同时**包含"爱"和"intp"的视频
- 更严格的过滤条件

**示例结果**：
- 只有ID=8同时包含两个词

### 4. 模糊搜索
```bash
# 英文模糊搜索（使用FTS通配符）
make search Q="int" FLAGS="--fuzzy"
# 匹配: int, intp, intj, into, integer...

# 中文模糊搜索（使用LIKE %x%）
make search Q="流浪" FLAGS="--fuzzy"
# 匹配: 流浪, 流浪汉, 流浪者...
```

### 5. 组合使用
```bash
# 多关键词 + AND逻辑 + 模糊搜索
make search Q="美 流浪" FLAGS="--match-all --fuzzy"

# 只在转写中搜索
make search Q="爱 intp" FLAGS="--field transcript"

# 显示所有匹配片段
make search Q="美国" FLAGS="--show-all-matches"
```

## 技术实现

### 相似度计算公式

**单关键词**：
- 使用BM25算法（FTS5内置）
- 或字符串匹配（中文）

**多关键词OR**：
```python
# 1. 收集每个关键词的匹配结果及分数
for keyword in keywords:
    results[video_id].scores.append(score)
    results[video_id].matched_count += 1

# 2. 计算综合分数
avg_score = sum(scores) / len(scores)          # 平均相关性
coverage = matched_count / total_keywords      # 覆盖率
final_score = avg_score * (0.7 + 0.3 * coverage)

# 示例：
# 视频A匹配1/2关键词，单词分数0.9
#   → 0.9 * (0.7 + 0.3 * 0.5) = 0.765
# 视频B匹配2/2关键词，平均分数0.8  
#   → 0.8 * (0.7 + 0.3 * 1.0) = 0.8 ✨ (更高)
```

**多关键词AND**：
```python
# 只保留matched_count == total_keywords的视频
# 然后应用相同的综合评分公式
```

### 模糊搜索实现

**英文**：
```python
# 自动添加FTS通配符
query = "int"  →  "int*"
# FTS搜索: MATCH 'int*'
```

**中文**：
```python
# 使用LIKE模式
query = "流浪"  →  "%流浪%"
# SQL: WHERE content LIKE '%流浪%'
```

## 搜索策略对比

| 场景 | 命令 | 匹配逻辑 | 适用情况 |
|------|------|---------|---------|
| 单词精确 | `Q="美国"` | 精确匹配 | 明确知道关键词 |
| 多词宽松 | `Q="爱 intp"` | OR，任一匹配 | 探索性搜索 |
| 多词严格 | `Q="爱 intp" --match-all` | AND，全部匹配 | 精确过滤 |
| 部分匹配 | `Q="int" --fuzzy` | 前缀/子串 | 不确定完整拼写 |
| 组合搜索 | `Q="美 流浪" --match-all --fuzzy` | AND+模糊 | 复杂需求 |

## 性能优化

1. **多关键词搜索**：
   - 单次查询limit=999，确保找到所有匹配
   - 在Python层面合并结果（避免复杂SQL）
   - 最后应用分页

2. **相似度缓存**：
   - 每个关键词的搜索结果独立计算
   - 综合评分在内存中快速完成

3. **中英文区分**：
   - 自动检测查询语言
   - 中文用LIKE，英文用FTS
   - 模糊搜索根据语言选择策略

## 示例场景

### 场景1：探索INTP相关内容
```bash
# 先宽松搜索
make search Q="intp 爱情 关系"
# → 找到7个结果，包含任一关键词

# 再精确搜索
make search Q="intp 爱情" FLAGS="--match-all"
# → 找到2个结果，同时讨论INTP和爱情
```

### 场景2：美国社会问题
```bash
# 模糊搜索"贫"字相关
make search Q="贫" FLAGS="--fuzzy"
# → 匹配：贫困、贫民、贫富...

# 多维度搜索
make search Q="美国 贫困 医疗"
# → OR逻辑，覆盖多个方面
```

### 场景3：不确定拼写
```bash
# 英文模糊
make search Q="infj" FLAGS="--fuzzy"
# → 匹配: infj, infp, intp, intj...

# 中文部分
make search Q="流" FLAGS="--fuzzy"
# → 匹配: 流浪、流量、流行...
```

## API使用

```python
from db import SearchRepository

repo = SearchRepository()

# 多关键词OR（默认）
results = repo.search(
    query="爱 intp",
    group_by_video=True,
    match_all_keywords=False  # OR逻辑
)

# 多关键词AND
results = repo.search(
    query="爱 intp",
    group_by_video=True,
    match_all_keywords=True  # AND逻辑
)

# 模糊搜索
results = repo.search(
    query="int",
    fuzzy=True  # 启用模糊匹配
)

# 组合使用
results = repo.search(
    query="美 流浪",
    match_all_keywords=True,  # AND
    fuzzy=True,               # 模糊
    min_relevance=0.8         # 最小相似度过滤
)
```

## 未来改进

1. **相似度权重调整**：允许用户自定义覆盖率权重
2. **关键词高亮**：在结果中标注匹配的关键词
3. **智能分词**：集成jieba等中文分词器
4. **同义词支持**：自动扩展相关词（如"美国"→"美利坚"）
5. **拼音搜索**：支持拼音输入查找中文内容
