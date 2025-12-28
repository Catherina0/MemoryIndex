# URL 智能提取功能

## 概述

系统现在支持从任意文本中自动提取视频 URL，用户无需手动复制粘贴链接，可以直接粘贴包含链接的分享文本。

## 支持的输入格式

### ✅ 纯 URL（直接链接）

```bash
make download-run URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
make download-ocr URL="https://www.bilibili.com/video/BV1ngCyBiEkc"
```

### ✨ 分享文本（自动提取）

```bash
# 微信/QQ 分享文本
make download-run URL="朋友推荐的视频：https://youtu.be/xxx 非常有趣"

# 社交媒体分享文本  
make download-ocr URL="B站分享 - https://b23.tv/abc123 - 必看"

# 带特殊字符的文本
make download-run URL="推荐看！→ https://www.bilibili.com/video/BVxxx ← 超棒"

# 聊天记录中的链接
make download-ocr URL="嘿，给你分享个视频：https://bilibili.com/video/BVxxx 看看吧"
```

## 识别的视频平台

### 🟢 YouTube

- `youtube.com/watch?v=...` - 完整链接（带参数）
- `youtu.be/...` - 短链接
- 示例：`https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s`

### 🟣 Bilibili（B站）

- `bilibili.com/video/BV...` - 完整链接
- `b23.tv/...` - 短链接
- 示例：`https://www.bilibili.com/video/BV1ngCyBiEkc?vd_source=...`

### 🔴 Xiaohongshu（小红书）

- `xiaohongshu.com/...` - 完整链接
- `xhslink.com/...` - 短链接
- 示例：`https://www.xiaohongshu.com/explore/...`

### 🟡 Douyin（抖音）

- `douyin.com/...` - 完整链接
- 示例：`https://www.douyin.com/video/...`

### 🐦 Twitter/X

- `twitter.com/...` - 完整链接
- `x.com/...` - X（新名称）链接
- 示例：`https://twitter.com/username/status/...`

## 自动处理功能

### 1️⃣ 文本解析

系统会从输入文本中查找所有匹配的 URL 模式：
- 检测 URL 前缀（http/https）
- 识别域名结构
- 捕获必需的参数

### 2️⃣ URL 清理

- **自动移除尾部标点符号**：
  - `链接）` → `链接`
  - `链接。` → `链接`
  - `链接"` → `链接`
  - `链接'` → `链接`
  - `链接]` → `链接`

- **保留必需参数**：
  - YouTube：保留查询参数 `?v=...`
  - Bilibili：保留 `vd_source` 等参数
  - 其他平台：根据需要保留路径和参数

### 3️⃣ 自动下载

提取 URL 后，系统自动：
1. 检测视频平台
2. 下载视频到 `videos/` 目录
3. 按标准格式命名：`标题_平台_视频ID.mp4`
4. 继续处理流程（音频/OCR）

## 工作流程

```
用户输入（可能包含额外文本）
        ↓
URL提取功能识别并提取 URL
        ↓
URL 有效性检查
        ↓
平台检测
        ↓
自动下载
        ↓
文件处理（ASR/OCR/总结）
```

## 错误处理

### ❌ 未找到 URL
如果输入文本中找不到任何有效的 URL：

```
❌ 错误：无法从输入中提取有效的视频URL
输入内容：这是一个不包含任何视频链接的普通文本

支持的URL格式：
  • YouTube: youtube.com/watch?v=... 或 youtu.be/...
  • Bilibili: bilibili.com/video/BV... 或 b23.tv/...
  • 小红书: xiaohongshu.com/... 或 xhslink.com/...
  • 抖音: douyin.com/...
  • Twitter/X: twitter.com/... 或 x.com/...
```

### ⚠️ URL 有效但视频不可用
如果 URL 格式正确但视频无法下载：
```
❌ 下载失败: youtube 平台视频下载失败: ...
```

## 使用建议

### ✅ 推荐做法
1. **复制整条分享链接**
   ```bash
   make download-run URL="朋友推荐：https://youtu.be/xxx 超级有趣的视频"
   ```

2. **粘贴聊天记录**
   ```bash
   # 包含前后文的聊天记录也可以
   make download-ocr URL="你看 https://b23.tv/abc 这个笑死我了 哈哈"
   ```

3. **使用任何包含 URL 的文本**
   ```bash
   # 甚至包含特殊字符、多个句子等
   make download-run URL="嘿！推荐你看！→ https://example.com/video ← 真的很好看。。。"
   ```

### ⚠️ 注意事项
1. **必须包含至少一个有效的视频 URL**
   - 不支持纯文本搜索（如"搜索关键词"）
   - 必须有明确的链接

2. **URL 应该可以被浏览器识别**
   - 支持 http:// 和 https://
   - 支持短链接和完整链接
   - 不支持自定义协议（如 magnet:）

3. **一次只提取第一个 URL**
   - 如果文本中包含多个视频链接，系统只会提取第一个
   - 其他链接可以分别处理

## 技术实现

### 核心函数
```python
def extract_url_from_text(text: str) -> Optional[str]:
    """从任意文本中提取视频URL"""
    # 定义 11 种视频平台的 URL 正则模式
    # 查找第一个匹配的 URL
    # 清理尾部标点符号
    # 返回清理后的 URL 或 None
```

### 正则模式示例
- YouTube: `https?://(?:www\.)?youtube\.com/watch\?v=[^&\s]+`
- Bilibili: `https?://(?:www\.)?bilibili\.com/video/[^\s?&]+`
- 短链接: `https?://b23\.tv/[^\s?&]+`

## 常见问题

### Q: 如果文本中有多个链接怎么办？
A: 系统会提取并使用第一个有效的链接。如果需要处理其他链接，请单独执行命令。

### Q: 支持移动端短链接吗？
A: 是的，支持所有常见的短链接格式（b23.tv, youtu.be, xhslink.com 等）

### Q: URL 提取失败时会怎样？
A: 系统会显示友好的错误提示，列出支持的 URL 格式和输入建议。

### Q: 提取的 URL 需要我再次确认吗？
A: 不需要。系统自动验证并开始下载。你可以在输出中看到识别的 URL。

### Q: 可以同时传入纯 URL 和分享文本吗？
A: 无需区分，系统会自动处理两种格式。无论是纯 URL 还是包含 URL 的文本都可以直接使用。

## 示例集合

### 场景 1：微信分享文本
```bash
# 原始分享文本
"分享一个B站视频给你：https://www.bilibili.com/video/BV1ngCyBiEkc?vd_source=99a0a798fd4f2116bab77eeef4b564e0 看看这个"

# 命令
make download-run URL="分享一个B站视频给你：https://www.bilibili.com/video/BV1ngCyBiEkc?vd_source=99a0a798fd4f2116bab77eeef4b564e0 看看这个"

# 结果：成功提取并下载
✅ 识别链接：https://www.bilibili.com/video/BV1ngCyBiEkc
✅ 开始下载...
```

### 场景 2：QQ 分享链接
```bash
# 原始分享文本
"强烈推荐 https://youtu.be/dQw4w9WgXcQ 这个视频 必看！！！"

# 命令
make download-ocr URL="强烈推荐 https://youtu.be/dQw4w9WgXcQ 这个视频 必看！！！"

# 结果：提取短链接并处理
✅ 识别链接：https://youtu.be/dQw4w9WgXcQ
✅ 开始下载...
```

### 场景 3：聊天记录（带特殊字符）
```bash
# 原始聊天记录
"嘿→ https://b23.tv/abc123 ←看看，很有趣哈哈哈"

# 命令
make download-run URL="嘿→ https://b23.tv/abc123 ←看看，很有趣哈哈哈"

# 结果：自动清理特殊字符
✅ 识别链接：https://b23.tv/abc123
✅ 开始下载...
```

## 更新日志

### v1.0 (2025-12-12)
- ✅ 实现 URL 提取功能
- ✅ 支持 6 个视频平台
- ✅ 自动尾部标点清理
- ✅ 友好的错误提示
- ✅ 完整的文档和示例
