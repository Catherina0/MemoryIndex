# 数据库系统 - 快速命令参考

## 📋 一键部署

```bash
# 方法 1: 使用部署脚本
./deploy_database.sh

# 方法 2: 使用 Makefile
make db-init && make db-test
```

---

## 🔍 搜索命令速查

### 全文搜索

```bash
# 基础搜索
make search Q="关键词"

# 在特定字段搜索
make search Q="关键词" FLAGS="--field transcript"  # 仅转写
make search Q="关键词" FLAGS="--field report"      # 仅报告
make search Q="关键词" FLAGS="--field ocr"         # 仅OCR

# 按时间排序
make search Q="关键词" FLAGS="--sort date"

# 按相关性排序（默认）
make search Q="关键词" FLAGS="--sort relevance"

# JSON 输出
make search Q="关键词" FLAGS="--json"

# 详细输出
make search Q="关键词" FLAGS="-v"
```

### 标签搜索

```bash
# 包含所有标签（AND逻辑）
make search-tags TAGS="标签1 标签2"

# 示例
make search-tags TAGS="教育 科技"
make search-tags TAGS="机器学习 深度学习 Python"
```

### 主题搜索

```bash
# 在主题中搜索
make search-topics Q="主题关键词"

# 示例
make search-topics Q="神经网络"
make search-topics Q="卷积"
```

---

## 🏷️ 标签管理

```bash
# 查看热门标签（Top 50）
make db-tags

# 标签自动补全
python search_cli.py suggest "前缀"

# 示例
python search_cli.py suggest "机器"  # → 机器学习、机器视觉...
```

---

## 🗄️ 数据库管理

```bash
# 初始化数据库
make db-init

# 查看状态
make db-status

# 运行测试
make db-test

# 备份数据库
make db-backup

# 优化数据库（定期维护）
make db-vacuum

# 重建数据库（⚠️ 删除所有数据）
make db-reset
```

---

## 🎯 常用工作流

### 工作流 1: 处理视频 → 搜索

```bash
# 1. 处理视频（自动入库）
make run VIDEO=video.mp4

# 2. 搜索刚处理的内容
make search Q="视频中的关键词"

# 3. 查看视频的标签
make db-tags
```

### 工作流 2: 批量处理 → 统计

```bash
# 1. 批量处理视频
for video in videos/*.mp4; do
    make run VIDEO="$video"
done

# 2. 查看数据库统计
make db-status

# 3. 查看热门标签
make db-tags
```

### 工作流 3: 搜索 → 导出

```bash
# 1. 搜索并导出 JSON
python search_cli.py search "关键词" --json > results.json

# 2. 查看结果
cat results.json | jq '.[].video_title'
```

---

## 📊 命令行工具高级用法

### search_cli.py 完整参数

```bash
# 全文搜索
python search_cli.py search "关键词" \
    --field transcript \      # 搜索字段: all/report/transcript/ocr/topic
    --tags 标签1 标签2 \       # 标签过滤
    --sort relevance \        # 排序: relevance/date/duration/title
    --limit 20 \              # 返回数量
    --offset 0 \              # 分页偏移
    --min-relevance 0.3 \     # 最小相关性（0-1）
    --json \                  # JSON输出
    -v                        # 详细输出

# 标签搜索
python search_cli.py tags \
    --tags 标签1 标签2 \       # 标签列表
    --match-all \             # 匹配所有标签（默认：任一）
    --limit 20 \
    --json

# 主题搜索
python search_cli.py topics "关键词" \
    --limit 20 \
    --json

# 列出标签
python search_cli.py list-tags --limit 50

# 标签自动补全
python search_cli.py suggest "前缀"
```

---

## 💡 快捷技巧

### 1. 快捷命令

```bash
# 搜索（简化版）
make s Q="关键词"

# 数据库状态（简化版）
make ds
```

### 2. 组合搜索

```bash
# 搜索+标签过滤+按时间排序
make search Q="深度学习" FLAGS="--tags 教育 --sort date"
```

### 3. 导出搜索结果

```bash
# 导出为 JSON
make search Q="关键词" FLAGS="--json" > results.json

# 导出为文本
make search Q="关键词" > results.txt
```

### 4. SQLite 直接查询

```bash
# 进入数据库
sqlite3 storage/database/knowledge.db

# 常用查询
SELECT title, duration_seconds FROM videos LIMIT 10;
SELECT name, count FROM tags ORDER BY count DESC LIMIT 20;
SELECT COUNT(*) FROM videos;
```

---

## 📈 性能优化

### 定期维护

```bash
# 每处理 1000 个视频后执行
make db-vacuum
```

### 备份策略

```bash
# 每周备份
make db-backup

# 查看备份
ls -lh storage/backups/
```

### 性能监控

```bash
# 查看数据库大小
make db-status

# 检查表统计
sqlite3 storage/database/knowledge.db "SELECT COUNT(*) FROM videos;"
sqlite3 storage/database/knowledge.db "SELECT COUNT(*) FROM artifacts;"
```

---

## 🔧 故障排查

### 问题 1: 搜索无结果

```bash
# 检查数据库是否有数据
make db-status

# 确认视频已处理
ls -lh output/
```

### 问题 2: 数据库文件不存在

```bash
# 重新初始化
make db-init
```

### 问题 3: 数据库锁定

```bash
# 解锁数据库
sqlite3 storage/database/knowledge.db "PRAGMA wal_checkpoint;"
```

### 问题 4: 想重新开始

```bash
# 清空数据库（需确认）
make db-reset
```

---

## 📚 完整文档

- **快速上手**: [DATABASE_QUICKSTART.md](./docs/DATABASE_QUICKSTART.md)
- **完整设计**: [DATABASE_DESIGN.md](./docs/DATABASE_DESIGN.md)
- **实施总结**: [DATABASE_SUMMARY.md](./docs/DATABASE_SUMMARY.md)
- **功能概览**: [DATABASE_README.md](./docs/DATABASE_README.md)

---

## 🎯 最佳实践

1. **首次使用**: 运行 `./deploy_database.sh`
2. **处理视频**: 使用 `make run` 或 `make ocr`（自动入库）
3. **定期备份**: 每周运行 `make db-backup`
4. **定期优化**: 每月运行 `make db-vacuum`
5. **搜索技巧**: 使用简短关键词，善用标签过滤

---

**🎉 现在你已掌握所有数据库命令！**

快速帮助: `make help`  
完整文档: `docs/DATABASE_*.md`
