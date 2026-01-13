# MemoryIndex

智能视频知识库系统 - 视频下载、OCR识别、全文搜索一体化解决方案

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3+-green.svg)](LICENSE)

## Installation

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

或一步完成：

```bash
brew install Catherina0/memoryindex/memoryindex
```

安装完成后立即可用，无需额外配置。

## Quick Start

```bash
# 搜索视频内容
memidx search "关键词"

# 列出所有视频
memidx list

# 查看视频详情
memidx show <ID>

# 处理本地视频（仅音频）
memidx-process video.mp4

# 处理本地视频（音频+OCR）
memidx-process video.mp4 --with-frames

# 下载并处理在线视频
memidx-download "https://www.youtube.com/watch?v=xxx"
memidx-download "https://www.bilibili.com/video/BVxxx"

# 归档网页内容为 Markdown
memidx-archive "https://www.zhihu.com/question/xxx"
```

## Features

### 📥 多平台视频下载
- **支持平台**: YouTube, Bilibili, 小红书, 抖音, Twitter/X
- **智能URL提取**: 直接粘贴分享文本，自动识别链接
- **自动降级策略**: yt-dlp → BBDown → XHS-Downloader

### 🎬 视频处理
- **音频转写**: Groq Whisper API（快速准确）
- **视频OCR**: **Apple Vision OCR** (macOS 原生，高精度，零配置)
- **AI摘要**: Groq GPT-OSS 120B（免费API）

### 🔍 智能搜索
- **全文搜索**: Whoosh + jieba 中文分词
- **多字段搜索**: 标题/转写/OCR/主题
- **标签系统**: 自动标签和主题管理
- **数据存储**: SQLite + Whoosh 索引

### 🌐 网页归档
- **支持平台**: 知乎、小红书、B站、Reddit、Twitter
- **智能提取**: 自动提取正文，排除评论/广告
- **Markdown输出**: 干净的 Markdown 格式
- **可选图片**: 支持下载图片

## Configuration

### Groq API（语音识别和AI摘要）

```bash
# 创建配置文件
echo "GROQ_API_KEY=your_key_here" > ~/.memoryindex.env

# 设置环境变量
export GROQ_ENV_FILE=~/.memoryindex.env

# 永久生效（添加到 shell 配置）
echo 'export GROQ_ENV_FILE=~/.memoryindex.env' >> ~/.zshrc
source ~/.zshrc
```

获取 API Key: https://console.groq.com/keys

### 可选依赖

```bash
# 网页归档功能
pip install crawl4ai playwright beautifulsoup4 html2text DrissionPage
```

**Note**: This version uses Apple Vision OCR (macOS native), no additional OCR setup needed.

## Commands Reference

### 搜索命令

```bash
# 全文搜索
memidx search "机器学习"

# 搜索特定字段
memidx search "Python" --field transcript
memidx search "代码" --field ocr

# 多关键词搜索
memidx search "Python 教程" --match-all

# 按标签搜索
memidx tags --tags 教育 科技 --match-all

# 主题搜索
memidx topics "神经网络"

# 列出热门标签
memidx list-tags --limit 20
```

### 处理命令

```bash
# 处理本地视频（仅音频）
memidx-process video.mp4

# 处理本地视频（音频 + OCR）
memidx-process video.mp4 --with-frames

# 下载并处理在线视频
memidx-download "https://www.youtube.com/watch?v=xxx"
memidx-download "https://www.bilibili.com/video/BVxxx"

# 仅下载不处理
memidx-download <URL> --download-only

# 归档网页
memidx-archive "https://zhuanlan.zhihu.com/p/xxx"
```

### 管理命令

```bash
# 列出所有视频
memidx list --limit 20

# 查看视频详情
memidx show 1

# 删除视频记录
memidx delete 1

# 数据库统计
memidx stats
```

## Testing

```bash
# Basic tests (no network)
memidx --help
memidx --version
memidx-process --help
memidx-download --help
memidx-archive --help

# System self-check (no API check)
memidx selftest

# Full self-check (includes API check)
memidx selftest -f
```

**Notes**:
- Basic `selftest` does not check API connectivity
- Only `selftest -f` validates Groq API connection
- Apple Vision OCR is used (no model download needed)

## Supported Platforms

### 视频平台
- **YouTube** - youtube.com, youtu.be
- **Bilibili** - bilibili.com, b23.tv
- **小红书** - xiaohongshu.com, xhslink.com
- **抖音** - douyin.com
- **Twitter/X** - twitter.com, x.com

### 网页归档平台
- **知乎** - 问题、回答、专栏
- **小红书** - 笔记、帖子
- **B站** - 专栏、视频简介
- **Reddit** - 帖子
- **Twitter/X** - 推文

## Project Structure

```
memoryindex/
├── cli/                    # 命令行界面
│   ├── search_cli.py      # 搜索命令
│   ├── archive_cli.py     # 归档命令
│   └── db_stats.py        # 统计命令
├── core/                   # 核心功能
│   ├── process_video.py   # 视频处理
│   ├── video_downloader.py # 视频下载
│   └── archive_processor.py # 归档处理
├── db/                     # 数据库层
│   ├── models.py          # 数据模型
│   ├── repository.py      # 数据访问
│   ├── search.py          # 搜索引擎
│   └── whoosh_search.py   # 全文索引
├── ocr/                    # OCR 模块
│   ├── ocr_vision.py      # Vision OCR
│   └── ocr_utils.py       # PaddleOCR
└── archiver/               # 网页归档
    ├── core/              # 爬虫核心
    ├── platforms/         # 平台适配器
    └── utils/             # 工具函数
```

## Performance

Performance reference based on test videos:

| Task | Time | Notes |
|------|------|-------|
| Audio transcription (10min video) | ~30s | Groq API |
| OCR (52 frames) | ~60s | Apple Vision |
| AI summary (3000 words) | ~5s | GPT-OSS 120B |

## Examples

### 处理 YouTube 视频

```bash
memidx-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 处理 B站视频

```bash
memidx-download "https://www.bilibili.com/video/BV1ngCyBiEkc"
```

### 搜索已处理的内容

```bash
memidx search "MBTI" --limit 5
memidx search "Python 教程" --field transcript
```

### 归档知乎回答

```bash
memidx-archive "https://www.zhihu.com/question/xxx/answer/xxx"
```

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

**Version**: 1.0.0  
**Last Updated**: 2026-01-13
