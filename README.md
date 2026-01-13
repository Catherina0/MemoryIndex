# MemoryIndex

智能视频知识库系统：从「视频/网页」到「可搜索知识库」的一整套流水线。

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3+-green.svg)](LICENSE)

---

## 1. 安装

### Homebrew（推荐普通用户）

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

或一步完成：

```bash
brew install Catherina0/memoryindex/memoryindex
```

### 源码安装（开发者）

```bash
git clone https://github.com/Catherina0/MemoryIndex.git
cd MemoryIndex

python3 -m venv .venv
source .venv/bin/activate

pip install -e .[archiver]
```

安装完成后，以下命令会出现在 PATH 中：

- `memidx` / `memoryindex`：主命令（搜索 / 处理 / 下载 / 归档 / 统计）
- `memidx-process`：仅视频处理（兼容旧用法）
- `memidx-download`：仅视频下载（兼容旧用法）
- `memidx-archive`：仅网页归档（兼容旧用法）

---

## 2. 快速开始（memidx 主命令）

```bash
# 1）配置 Groq API（语音识别 + AI 摘要）
echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env
export GROQ_ENV_FILE=~/.memoryindex.env

# 2）处理本地视频
memidx process /path/to/video.mp4                 # 音频转写 + AI 摘要
memidx process /path/to/video.mp4 --ocr           # + OCR 识别（画面文字）

# 3）下载并处理在线视频
memidx download "https://www.youtube.com/watch?v=xxx" --process
memidx download "https://www.bilibili.com/video/BVxxx" --process --ocr

# 4）搜索已处理内容
memidx search "机器学习"                          # 全文搜索
memidx search "Python" --field transcript        # 只搜语音转写
memidx search "字幕"  --field ocr                # 只搜 OCR 文本

# 5）归档网页为 Markdown
memidx archive "https://www.zhihu.com/question/xxx/answer/yyy"

# 6）查看统计与自检
memidx stats
memidx selftest          # 快速自检
memidx selftest --full   # 含 API 连通性检测
```

---

## 3. 核心功能

### 📥 多平台视频下载

- 支持：YouTube、Bilibili、小红书、抖音、Twitter/X 等
- 智能 URL 提取：直接粘贴分享文案，自动识别链接
- 自动降级策略：`yt-dlp → BBDown → XHS-Downloader`
- 统一下载目录：默认保存到 `videos/`

### 🎬 视频处理流水线

- 音频转写：Groq Whisper API（快且便宜）
- 画面 OCR：Apple Vision OCR（macOS 原生，零配置；其他平台可选 PaddleOCR）
- AI 摘要：Groq GPT-OSS 120B（长文本理解与结构化报告）
- 输出内容：
    - 结构化报告（摘要、要点、章节）
    - 语音转写全文
    - OCR 识别文本
    - 元数据（标题、平台、时长、标签、主题）

### 🔍 智能搜索与标签

- Whoosh + jieba 中文分词
- 多字段搜索：标题 / 报告 / 转写 / OCR / 主题
- 标签系统：自动标签 + 手动标签
- 主题聚类：按主题视角浏览视频

### 🌐 网页归档（Web Archiver）

- 支持：知乎、小红书、B 站专栏、Reddit、Twitter/X 等
- 精准正文提取：自动排除评论区、推荐列表、广告
- 输出：干净的 Markdown（可选图片）
- 与数据库集成：可选把网页内容也纳入统一搜索/统计

---

## 4. 命令一览（memidx）

```bash
memidx --help
```

### 搜索与浏览

```bash
memidx search "机器学习"                        # 全文搜索
memidx search "Python" --field transcript      # 仅语音转写
memidx search "字幕" --field ocr               # 仅 OCR 文本
memidx search "深度 学习" --match-all          # 多关键词 AND

memidx tags --tags 教育 科技 --match-all        # 按标签搜索
memidx topics "神经网络"                        # 按主题搜索
memidx list                                      # 列出所有视频
memidx show 123                                  # 查看 ID=123 的详情
memidx delete 123                                # 删除记录（需确认）
```

### 视频处理

```bash
# 本地视频
memidx process video.mp4                         # 音频 + 摘要
memidx process video.mp4 --ocr                   # 音频 + OCR + 摘要

# 在线视频
memidx download "https://youtu.be/xxx" --process
memidx download "https://www.bilibili.com/video/BVxxx" --process --ocr

# 强制重新下载
memidx download "URL" --process --force
```

### 网页归档

```bash
memidx archive "https://www.zhihu.com/question/xxx/answer/yyy"
memidx archive "https://www.bilibili.com/read/cv123456"
```

### 系统维护

```bash
memidx selftest             # 快速自检（不访问外网）
memidx selftest --full      # 完整自检（含 Groq API）
memidx config               # 交互式配置向导
memidx stats                # 数据库统计信息
```

> 兼容旧用法：`memidx-process` / `memidx-download` / `memidx-archive`
> 推荐逐步迁移到统一的 `memidx process` / `memidx download` / `memidx archive`。

---

## 5. Makefile 快捷命令

在源码目录中，还可以使用 `make` 进行一键操作：

```bash
make setup                          # 初始化虚拟环境和依赖

make run VIDEO=video.mp4           # 本地视频：音频 + 摘要
make ocr VIDEO=video.mp4           # 本地视频：音频 + OCR + 摘要

make download URL=链接             # 只下载
make download-run URL=链接         # 下载后自动处理（音频）
make download-ocr URL=链接         # 下载后自动处理（含 OCR）

make archive URL=网址              # 仅归档网页为 Markdown
make archive-run URL=网址          # 归档 + AI 报告 + 入库
make archive-batch FILE=urls.txt   # 批量归档

make search Q="关键词"            # 命令行搜索封装
make db-stats                      # 数据库统计
```

---

## 6. 配置说明

### Groq API（必需）

```bash
echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env
export GROQ_ENV_FILE=~/.memoryindex.env
echo 'export GROQ_ENV_FILE=~/.memoryindex.env' >> ~/.zshrc
source ~/.zshrc
```

获取 API Key: https://console.groq.com/keys

### OCR 引擎

- macOS：默认使用 Apple Vision OCR（免安装、免配置）
- 其他平台：可选安装 PaddleOCR：

```bash
make install-paddle-ocr
```

### 网页归档依赖

```bash
pip install "memoryindex[archiver]"
make install-chromium   # 安装 Playwright Chromium
```

如需登录后才能访问的站点（小红书、知乎）：

```bash
make config-xhs-cookie      # 配置小红书 Cookie
make config-zhihu-cookie    # 配置知乎 Cookie
```

---

## 7. 项目结构

```
cli/                    # 统一 CLI 入口与子命令
    main_cli.py           # memidx 主命令
    search_cli.py         # 搜索相关实现
    archive_cli.py        # 网页归档 CLI
    db_stats.py           # 统计命令

core/                   # 核心流水线
    process_video.py      # 视频处理（转写 + OCR + 摘要）
    video_downloader.py   # 视频下载（多平台）

db/                     # 数据库与搜索
    models.py             # ORM 模型
    repository.py         # 数据访问封装
    search.py             # 搜索字段/选项定义
    whoosh_search.py      # Whoosh 全文索引

ocr/                    # OCR 封装
    ocr_vision.py         # Apple Vision OCR
    ocr_utils.py          # PaddleOCR 适配

archiver/               # 网页归档器
    core/                 # Crawl4AI/Playwright 封装
    platforms/            # 各平台解析（知乎/小红书/B站等）
    utils/                # Cookie 管理、URL 解析等
```

---

## 8. 示例

```bash
# 处理一个 B 站视频（含 OCR）
memidx download "https://www.bilibili.com/video/BV1ngCyBiEkc" --process --ocr

# 搜索「MBTI」相关内容
memidx search "MBTI" --limit 5

# 归档知乎高赞回答
memidx archive "https://www.zhihu.com/question/xxx/answer/yyy"
```

核心功能（下载 → 处理 → 入库 → 搜索 / 统计 / 归档）已经全部打通，
可以直接当成「个人视频+网页知识库」来用。

## Troubleshooting

### ffmpeg 未找到

```bash
brew install ffmpeg
```

### Groq API 未配置

```bash
# 1. 获取 API Key
open https://console.groq.com/keys

# 2. 创建配置文件
echo "GROQ_API_KEY=gsk_xxx" > ~/.memoryindex.env
export GROQ_ENV_FILE=~/.memoryindex.env
```

### PaddleOCR 模型下载慢

```bash
# 跳过源检查
export DISABLE_MODEL_SOURCE_CHECK=True
```

### 验证安装

```bash
# 检查版本
memidx --version

# 系统自检
memidx selftest

# 完整检查（含API）
memidx selftest -f
```

## Documentation

- **快速参考**: [CHEATSHEET.txt](CHEATSHEET.txt) - 常用命令速查
- **使用指南**: [USAGE.md](USAGE.md) - 详细使用说明
- **Groq配置**: [docs/GROQ_SETUP.md](docs/GROQ_SETUP.md) - API 配置指南
- **OCR优化**: [docs/OCR_MODELS.md](docs/OCR_MODELS.md) - OCR 模型选择
- **下载指南**: [docs/DOWNLOAD_GUIDE.md](docs/DOWNLOAD_GUIDE.md) - 视频下载功能
- **归档指南**: [docs/ARCHIVER_GUIDE.md](docs/ARCHIVER_GUIDE.md) - 网页归档功能

## Requirements

- **Python**: 3.8+
- **macOS**: Required for Apple Vision OCR
- **ffmpeg**: Audio/video processing (`brew install ffmpeg`)

## Alternative Installation

### pip 安装（开发版）

```bash
# 从 GitHub 安装
pip install git+https://github.com/Catherina0/MemoryIndex.git

# 或克隆仓库
git clone https://github.com/Catherina0/MemoryIndex.git
cd MemoryIndex
pip install -e .
```

### 可选依赖组

```bash
# 网页归档
pip install -e ".[archiver]"

# 完整功能
pip install -e ".[full]"
```

## Contributing

欢迎提交 Issue 和 Pull Request！

## License

GPLv3+ - 详见 [LICENSE](LICENSE)

## Links

- **GitHub**: https://github.com/Catherina0/MemoryIndex
- **Issues**: https://github.com/Catherina0/MemoryIndex/issues
- **Homebrew Tap**: https://github.com/Catherina0/homebrew-memoryindex
- **Groq API**: https://console.groq.com
- **yt-dlp**: https://github.com/yt-dlp/yt-dlp
- **PaddleOCR**: https://github.com/PaddlePaddle/PaddleOCR

---

**Version**: 1.0.4  
**Last Updated**: 2026-01-13
