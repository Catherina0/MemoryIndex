# 🔄 视频处理改进总结

## 📝 本次更新内容

### 最新更新（2024年12月26日）

#### ⚡ GPU 加速支持

**核心功能：**
- ✅ 为 OCR 模块添加 GPU 加速支持
- ✅ 自动检测 GPU 可用性
- ✅ 支持强制使用 GPU 或 CPU
- ✅ 3-5倍性能提升（GPU vs CPU）
- ✅ 修复 PaddleOCR 3.x 版本兼容性问题

**技术细节：**
- PaddleOCR 3.x 不再接受 `use_gpu` 参数
- 使用 `paddle.device.set_device()` 控制设备
- 自动检测并设置 GPU 或 CPU 模式
- 更新参数名称以匹配新版 API（如 `use_textline_orientation`、`text_det_thresh` 等）

**修改文件：**
- `ocr_bilingual.py` - 添加 GPU 支持和检测功能，使用正确的 PaddleOCR 3.x 参数
- `ocr_utils.py` - init_ocr 支持自动 GPU 检测，使用 paddle.device.set_device
- `process_video.py` - 已支持 --use-gpu 参数
- `test_gpu.py` - 新增 GPU 性能测试脚本

**新增文档：**
- `docs/GPU_ACCELERATION.md` - GPU 加速完整配置指南
- `docs/GPU_EXAMPLES.md` - GPU 加速使用示例
- `GPU_QUICKSTART.md` - GPU 加速快速入门

**使用方法：**
```bash
# 自动检测 GPU（推荐）
python process_video.py video.mp4 --with-frames

# 强制使用 GPU
python process_video.py video.mp4 --with-frames --use-gpu

# 双语言 OCR 工具
python ocr_bilingual.py image.png --gpu

# GPU 性能测试
python test_gpu.py image.png --compare
```

**性能对比：**
| 模式 | 耗时 | 加速比 |
|------|------|--------|
| CPU (server + server) | ~180秒 | 1.0x |
| GPU (server + server) | ~40-60秒 | 3-4.5x |

**已知问题修复：**
- ✅ 修复 `ValueError: Unknown argument: use_gpu` 错误
- ✅ 更新为 PaddleOCR 3.x 兼容的参数名称
- ✅ 使用 paddle.device.set_device 代替 use_gpu 参数

---

### 1. AI 提示词优化

**标签生成规则：**
- ✅ 3-6个高度概括的主题标签
- ✅ 简短（1-4个字），如"情感"、"告白"、"人生意义"、"科技"、"教育"
- ❌ 避免技术性描述词，如"语音转写"、"OCR推断"
- ✅ 概括性强，便于数据库搜索

**摘要生成规则：**
- ✅ 不超过50个字
- ✅ 系统性概括核心主题和要点
- ✅ 独立的"## 摘要"章节

### 2. 数据提取增强

**`extract_summary_from_report()`**
- 从AI报告中智能提取"## 摘要"章节
- 自动清理Markdown格式
- 限制长度为50字
- 后备方案：提取第一段有效内容

**`extract_tags_from_summary()` 改进**
- 支持"## 标签"章节格式
- 更强大的清理逻辑（移除Markdown、引号、换行）
- 支持多种分隔符（逗号、顿号、分号等）

### 3. 数据库显示优化

**`list_videos()` 改进**
- 使用提取的摘要代替原始文本截取
- 标签正确显示在列表中
- 摘要长度控制在50字以内

## 🎯 使用示例

### 处理新视频
```bash
# 音频模式
make run VIDEO=/path/to/video.mp4

# OCR模式
make ocr VIDEO=/path/to/video.mp4

# 从URL
make download-run URL="https://..."
```

**处理完成后自动提取：**
- 🏷️ 标签：情感、告白、人生意义（3-6个）
- 📝 摘要：不超过50字的核心概括
- 📚 主题：章节结构
- ⏱️ 时间线：逐秒对照（OCR模式）

### 查看结果
```bash
# 列出所有视频（显示标签和摘要）
make db-list

# 按标签搜索
make search-tags TAGS="情感 人生意义"

# 全文搜索
make search Q="告白"
```

## 📊 预期输出格式

### AI 报告结构
```markdown
## 摘要
视频讲述了INTP性格类型的核心特点，强调其独特的认知方式与目标设定。

## 详细的主要内容概括
...

## 标签
标签: 心理学, INTP, 性格分析, 自我认知
```

### 数据库列表显示
```
+-----+------+------------------+----------+--------+----------------------------+------------------------------------------+
|   # |   ID | 标题             | 来源     | 时长   | 标签                       | 摘要                                     |
+=====+======+==================+==========+========+============================+==========================================+
|   1 |    1 | INTP性格分析     | bilibili | 15:30  | 心理学, INTP, 性格分析...  | 视频讲述了INTP性格类型的核心特点，强调... |
```

## 🔍 标签质量对比

### ❌ 之前（技术性描述）
- 语音转写
- OCR推断
- 数据整理
- 视频处理

### ✅ 现在（概括性主题）
- 心理学
- 情感
- 人生意义
- 自我认知

## 🛠️ 技术细节

### 提示词关键改动

**旧版：**
```
6. 为未来检索生成若干关键词（tags）
## 标签（tags）
```

**新版：**
```
6. 生成标签和摘要：
   - 标签（tags）：3-6个高度概括的主题标签，如"情感"、"告白"、"人生意义"等
   - 摘要：不超过50个字的系统性内容概括

## 摘要
（不超过50字的核心内容概括）

## 标签
格式：标签: 标签1, 标签2, 标签3
```

### 提取函数增强

**摘要提取：**
```python
# 支持多种格式
r'##\s*摘要\s*\n+(.+?)(?:\n\n|\n##)'  # ## 摘要
r'摘要[：:]\s*(.+?)(?:\n\n|\n##)'     # 摘要:

# 清理Markdown
extracted = re.sub(r'\*\*|\*|`|#|\[|\]|\(.*?\)', '', extracted)

# 限制长度
if len(extracted) > 50:
    extracted = extracted[:50] + '...'
```

**标签提取：**
```python
# 支持章节格式
r'##\s*标签\s*\n+(.+?)(?:\n\n|\n##)'

# 强化清理
clean_match = re.sub(r'\*\*|\*|`|#', '', match)
clean_match = re.sub(r'["""\'\'"]', '', clean_match)
clean_match = clean_match.replace('\n', ' ')

# 多分隔符支持
tag_list = re.split(r'[,，、\s;；]+', clean_match.strip())
```

## ✅ 验证清单

- [x] AI 提示词更新
- [x] 摘要提取函数实现
- [x] 标签提取函数增强
- [x] 数据库显示优化
- [ ] 完整流程测试（需要处理新视频）
- [ ] 时长信息补充

## 📌 待办事项

### ✅ 已解决（2024-12-26 03:50）

1. **时长问题** ✅ **已修复**
   - **问题**：视频时长显示 N/A，数据库中 `duration_seconds` 为 0
   - **原因**：尝试从 `transcript_data.get('duration')` 获取，但 Groq API 不返回时长
   - **解决方案**：
     - 添加 `get_video_duration()` 函数（process_video.py 第35-57行）
     - 使用 ffprobe 直接从视频文件元数据获取时长
     - 在处理流程开始时获取并传递给数据库
   - **测试结果**：✅ 成功获取并保存 279.48 秒

2. **标签重复问题** ✅ **已修复**
   - **问题**：每个标签在列表中显示两次
   - **原因**：SQL 的 `LEFT JOIN artifacts` 导致笛卡尔积（多个artifact记录）
   - **解决方案**：
     - 改用子查询避免 JOIN 导致的重复
     - 分别查询 tags 和 report_content（db/repository.py 第307-331行）
   - **测试结果**：✅ 标签不再重复

### 🔜 后续优化

1. **完整测试**：处理一个新视频验证时长和标签的完整流程
2. **旧数据更新**：可选地重新处理旧视频以更新标签和摘要

## 💡 使用建议

1. **新视频处理**：直接使用 `make run` 或 `make ocr`，会自动应用新规则
2. **旧数据**：标签和摘要质量可能不佳，可以考虑重新处理重要视频
3. **标签搜索**：现在可以用更自然的词搜索，如 `make search-tags TAGS="情感 人生"`
