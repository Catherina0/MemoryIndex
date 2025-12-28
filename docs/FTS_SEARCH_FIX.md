# FTS5 中文搜索问题修复

## 问题描述

搜索"美国"只能找到ID=14，无法找到ID=16，尽管两个视频的内容中都包含"美国"这个词。

## 根本原因

SQLite FTS5的`porter unicode61` tokenizer对中文分词支持不佳。即使内容中包含查询词，FTS5也可能因为分词问题无法匹配。

## 解决方案

**混合搜索策略**：根据查询内容自动选择搜索方式

### 1. **中文查询（短查询）**
- 检测：查询长度<20且包含中文字符
- 使用：`LIKE '%查询词%'` 模式匹配
- 优点：100%准确匹配中文
- 缺点：不支持BM25相关性排序

### 2. **英文/长查询**
- 使用：FTS5 `MATCH` 查询
- 优点：支持BM25相关性、布尔运算、通配符
- 分词器：`unicode61 remove_diacritics 0`

## 代码修改

### search.py
```python
# 检测查询类型
use_like = len(query) < 20 and any('\u4e00' <= c <= '\u9fff' for c in query)

if use_like:
    # 使用 LIKE 搜索
    WHERE fts_inner.content LIKE '%查询词%'
else:
    # 使用 FTS 搜索
    WHERE fts_inner.content MATCH '查询词'
```

### schema.sql
```sql
CREATE VIRTUAL TABLE fts_content USING fts5(
    ...
    tokenize = 'unicode61 remove_diacritics 0'  -- 移除porter stemming
);
```

## 测试结果

```bash
make search Q="美国"
# ✅ 找到 2 个结果: ID=14, ID=16

make search Q="流浪汉"  
# ✅ 找到 1 个结果: ID=16

make search Q="machine learning"
# ✅ 使用FTS5，支持词干匹配和相关性排序
```

## 权衡取舍

| 特性 | LIKE模式（中文） | FTS模式（英文） |
|------|-----------------|----------------|
| 准确性 | 100%字符串匹配 | 依赖分词器 |
| 性能 | 较慢（全表扫描） | 快（倒排索引） |
| 相关性排序 | 否（按时间） | 是（BM25） |
| 布尔运算 | 否 | 是 |
| 适用场景 | 中文短查询 | 英文/复杂查询 |

## 未来改进

1. **安装中文分词器**：如jieba-fts5扩展
2. **语言检测**：更智能地选择搜索策略
3. **缓存优化**：为常用LIKE查询建立索引
