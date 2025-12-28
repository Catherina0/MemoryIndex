# 准确搜索 vs 模糊搜索

## 核心差别

| 特性 | 准确搜索 | 模糊搜索 |
|------|---------|---------|
| 匹配方式 | 完全匹配 | 前缀/子串匹配 |
| 搜索范围 | 更严格 | 更宽松 |
| 英文实现 | FTS MATCH "int" | FTS MATCH "int*" |
| 中文实现 | LIKE "%流浪汉%" | LIKE "%流浪%" |
| 精度 | 高 | 中 |
| 召回率 | 低 | 高 |
| 适用场景 | 明确关键词 | 不确定拼写/词形 |

## 详细对比

### 1. 英文搜索

#### 准确搜索：`make search Q="int"`
```python
# SQL实现：FTS MATCH 'int'
# 匹配：
#   - int（精确单词）
#   - interest, interior, integer（包含"int"的单词）
# 
# 不匹配：
#   - in, it, i（更短的词）
```

**示例结果：**
```
搜索: "int"
找到 1 个结果:
  - ID=13: INTP：你不是迷茫... (相关性 0.88)
    ├─ 精确匹配"int"在INTP中
```

#### 模糊搜索：`make search Q="int" FLAGS="--fuzzy"`
```python
# SQL实现：FTS MATCH 'int*'
# 匹配：
#   - int, ints（int开头的词）
#   - integer, international, internal...
#   - intp, intj, intro...
#
# 不匹配：
#   - count, hint, print（int在末尾）
```

**示例结果：**
```
搜索: "int" --fuzzy
找到 1 个结果:
  - ID=13: INTP：你不是迷茫... (相关性 0.88)
    ├─ 模糊匹配INTP中的"int"前缀
```

### 2. 中文搜索

#### 准确搜索：`make search Q="流浪汉"`
```python
# SQL实现：LIKE '%流浪汉%'
# 匹配：
#   - 流浪汉（精确3字词）
#   - "这个流浪汉很可怜"（包含该词）
#   - "流浪汉群体"（词的组合）
#
# 不匹配：
#   - 流浪者（不同词）
#   - 流浪（缺少"汉"）
```

**示例结果：**
```
搜索: "流浪汉"
找到 1 个结果:
  - ID=16: 甜甜圈被保释，开启一场残酷社会实验...
    └─ 内容包含"沦为街头流浪汉"
```

#### 模糊搜索：`make search Q="流浪" FLAGS="--fuzzy"`
```python
# SQL实现：LIKE '%流浪%'
# 匹配：
#   - 流浪（2字词）
#   - 流浪汉、流浪者、流浪民...
#   - "街头流浪"、"流浪生活"...
#   - "在荒野中流浪"
#
# 优点：不需要完整词形，对多种表达都适用
```

**示例结果：**
```
搜索: "流浪" --fuzzy
找到 1 个结果：
  - ID=16: 甜甜圈被保释，开启一场残酷社会实验...
    └─ 内容包含"沦为街头流浪汉"（匹配了"流浪"部分）
```

## 使用场景决策树

```
搜索需求
├─ 明确完整词汇
│  ├─ 英文: "machine learning"  → 准确搜索 ✓
│  └─ 中文: "斩杀线"           → 准确搜索 ✓
│
├─ 不确定完整拼写
│  ├─ 英文: "mach..."  → 模糊搜索 (匹配machine, match...)
│  └─ 中文: "斩..."    → 模糊搜索 (匹配斩杀线, 斩断...)
│
├─ 查找词的变形
│  ├─ 英文: "run*"  → 模糊搜索 (匹配run, runs, running...)
│  └─ 中文: "流*"   → 模糊搜索 (匹配流浪, 流量, 流行...)
│
└─ 探索性搜索/宽松匹配
   └─ 两者都可用，模糊搜索更可能找到结果
```

## 实际例子

### 例子1：某人想找INTP相关的内容

**场景A：知道确切词汇**
```bash
# 准确搜索"INTP"
make search Q="INTP"
# 结果：找到7个相关视频
# - ID=13: INTP：你不是迷茫... (0.88)
# - ID=8:  INFJ_·_INFP_·_INTP_·_INTJ... (0.87)
```

**场景B：不确定大小写**
```bash
# 模糊搜索"intp"（小写）
make search Q="intp" FLAGS="--fuzzy"
# 使用FTS MATCH 'intp*'
# 结果：同样找到7个视频
# 因为FTS是case-insensitive的
```

### 例子2：找"流浪"相关内容

**准确搜索vs模糊搜索**
```bash
# 准确：必须完整匹配"流浪汉"
make search Q="流浪汉"
# 结果：找到1个（ID=16）
# 因为只有这个视频明确提到"流浪汉"

# 模糊：匹配"流浪"开头的任何词
make search Q="流浪" FLAGS="--fuzzy"
# 结果：找到1个（ID=16）
# 因为内容中有"街头流浪汉"
# 即使搜"流"或"浪"也可能命中
```

### 例子3：英文科学词汇

**准确：要找"neural network"**
```bash
make search Q="neural"
# FTS MATCH 'neural'
# 精确匹配包含"neural"的文本
```

**模糊：想找所有"neur-"开头的词**
```bash
make search Q="neur" FLAGS="--fuzzy"
# FTS MATCH 'neur*'
# 匹配: neural, neuron, neurological, neuroscience...
```

## 性能影响

| 搜索类型 | 速度 | 数据库负载 | 结果数 |
|---------|------|-----------|-------|
| 准确搜索 | 快 | 低 | 少（高精度） |
| 模糊搜索 | 中 | 中 | 多（高召回） |

**原因：**
- FTS `MATCH 'int*'` 需要扫描更多token
- LIKE `%流浪%` 需要全表扫描（无索引优化）
- 但因为数据库较小，差异不明显

## 实现细节

### 英文模糊搜索的工作原理

```python
# 用户输入：Q="int" --fuzzy
# 系统处理：
query = "int"
if fuzzy and not has_chinese:
    query = f"{query}*"  # → "int*"

# SQL：
WHERE content MATCH "int*"

# FTS5分词：
# "INTP：你不是迷茫" → 分词 → ["INTP", "你", "不是", "迷茫"]
# "interesting topic" → ["interesting", "topic"]
# 
# "int*" 匹配规则（前缀）：
# ✓ int 前缀的 token：INTP, interesting...
# ✗ 不是前缀：print, hint, count...
```

### 中文模糊搜索的工作原理

```python
# 用户输入：Q="流浪" --fuzzy
# 系统处理：
query = "流浪"
fuzzy = True
use_like = True  # 中文总是用LIKE

pattern = f"%{query}%"  # → "%流浪%"

# SQL：
WHERE content LIKE "%流浪%"

# 字符串匹配：
# "街头流浪汉" → 包含 "流浪" → ✓
# "流浪人生" → 包含 "流浪" → ✓
# "离家远航" → 不包含 "流浪" → ✗
```

## 建议规则

### 使用准确搜索的场景
✓ 知道完整、精确的关键词  
✓ 追求高精度、少结果  
✓ 关键词通常作为完整单词出现  
✓ 中文关键词完整（如"斩杀线"）  

### 使用模糊搜索的场景
✓ 关键词不确定完整形式  
✓ 想覆盖词的变形（running, runs, run...）  
✓ 中文词可能有多种搭配（流浪 → 流浪汉、流浪者...）  
✓ 做探索性搜索，想要更多结果  
✓ 用户输入可能有拼写错误  

## 常见问题

### Q: 为什么搜"int"和"int*"结果一样？
A: 在这个数据库中，恰好只有"INTP"一个词包含"int"前缀，所以结果相同。如果有更多"inter-", "intro-"开头的词，模糊搜索就会显示差异。

### Q: 中文搜索为什么没有真正的"模糊匹配"？
A: 因为中文分词困难，SQLite FTS5对中文支持有限。我们采用了LIKE子串匹配作为替代方案。理想方案是集成jieba等中文分词器。

### Q: 哪个更快？
A: 准确搜索通常更快，因为FTS索引更有效。但在这个数据库规模上，差异可忽略。

### Q: 能结合使用吗？
A: 可以！
```bash
# 多关键词 + 模糊搜索
make search Q="流浪 生活" FLAGS="--fuzzy"
# 找包含"流浪*"或"生活*"的视频

# 多关键词AND + 模糊搜索
make search Q="流浪 困境" FLAGS="--match-all --fuzzy"
# 找同时包含"流浪*"和"困境*"的视频
```

## 总结表

| 搜索方式 | 匹配逻辑 | 英文例子 | 中文例子 |
|---------|---------|---------|---------|
| **准确** | 完全匹配 | `Q="int"` → int, INTP | `Q="流浪汉"` → 流浪汉 |
| **模糊** | 前缀匹配 | `Q="int" --fuzzy` → int*, intp, integer | `Q="流浪" --fuzzy` → 流浪, 流浪汉, 流浪者 |
| **多词OR** | 任一匹配 | `Q="int love"` → 包含int或love | `Q="流浪 爱"` → 包含流浪或爱 |
| **多词AND** | 全部匹配 | `Q="int love" --match-all` → 同时包含int和love | `Q="流浪 困境" --match-all` → 同时包含流浪和困境 |
