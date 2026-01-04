# MemoryIndex - 智能视频知识库系统

一个智能视频处理系统，从在线下载到离线分析，全流程自动化。

> 🎉 **现在可以全系统使用！** 安装后在任何目录运行 `mi search "关键词"` 即可搜索！

## 🚀 一分钟快速开始

```bash
# 1. 一键安装（全系统可用）
./install.sh

# 2. 立即搜索
mi search "关键词"

# 3. 处理新视频
mi-process video.mp4
```

**就这么简单！** 查看 [快速参考](QUICKREF.md) 了解更多命令。

---

## 🎯 核心功能

### 📥 **统一视频下载层**（新增）
- 🌐 多平台支持：YouTube, Bilibili, 小红书, 抖音, Twitter/X
- 🤖 智能 URL 提取：直接粘贴分享文本，自动识别链接
- 🔄 自动降级策略：yt-dlp → BBDown → XHS-Downloader
- 📱 分享友好：支持微信、QQ、聊天记录等各种分享格式
- 📁 统一命名：所有平台视频统一格式 `标题_平台_视频ID.mp4`

### 🎬 **视频处理管道**
- **抽帧** - 使用 ffmpeg 从视频提取帧（支持自定义频率）
- **音频分离** - 提取视频中的音频并转换为 WAV 格式  
- **本地 OCR** - 使用 PaddleOCR 对提取的帧进行文字识别（支持多语言，支持GPU加速）
- **语音识别** - 集成 Groq API 实现实时语音转文字（Whisper 大模型）

### 📝 **智能总结生成**
- 合并 OCR 和音频识别结果
- 使用 Groq GPT-OSS 120B 进行智能摘要
- 生成格式化的完整报告
- 支持自定义输出目录

### ⚡ **自动化环境管理**
- 首次运行自动创建虚拟环境
- 自动安装所有依赖包
- 自动检测和配置系统环境
- **全系统可用**：安装后在任何目录使用 `mi` 命令

### 🔍 **智能搜索系统**（新增）
- **全文搜索**：支持中文分词的全文检索
- **多字段搜索**：可搜索标题、描述、OCR文本、转写内容
- **标签系统**：智能标签分类和搜索
- **主题管理**：按主题组织和查找内容
- **命令行界面**：强大的 CLI 工具，随时随地搜索

---

## 📦 安装方式

### 方式 1：一键安装（推荐）

```bash
./install.sh
```

安装后全系统可用：

```bash
mi search "关键词"          # 搜索视频内容
mi list                     # 列出所有视频
mi topics                   # 查看主题
mi-process video.mp4        # 处理新视频
```

### 方式 2：开发模式

```bash
pip install -e .
```

- ✅ 代码修改立即生效
- ✅ 适合开发和调试

### 方式 3：Homebrew（高级）

创建你自己的 Homebrew Tap：

```bash
brew tap Catherina0/memoryindex
brew install memoryindex
```

详细步骤查看 [PACKAGING.md](PACKAGING.md)

---

## 🎯 使用命令

### 搜索功能

```bash
# 全文搜索
mi search "机器学习"

# 搜索转写内容
mi search "人工智能" --field transcript

# 搜索 OCR 文本
mi search "代码示例" --field ocr

# 多关键词搜索
mi search "Python 教程"
mi search "Python OR JavaScript"
```

### 浏览和管理

```bash
# 列出所有视频
mi list

# 查看最近的10个视频
mi list --limit 10 --sort-by date --desc

# 查看所有主题
mi topics

# 按标签搜索
mi tags --tags 教育 科技

# 查看视频详情
mi show 1
```

### 处理视频

```bash
# 处理本地视频
mi-process video.mp4

# 使用项目Makefile（传统方式）
make run VIDEO=video.mp4
make ocr VIDEO=video.mp4
```

更多命令查看 [QUICKREF.md](QUICKREF.md) 或运行 `mi --help`

---

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [QUICKREF.md](QUICKREF.md) | 📝 快速参考卡 - 常用命令速查 |
| [USAGE.md](USAGE.md) | 🎯 使用指南 - 详细使用说明 |
| [INSTALL.md](INSTALL.md) | 📖 安装指南 - 各种安装方式 |
| [PACKAGING.md](PACKAGING.md) | 📦 打包指南 - 发布和分发 |
| [alias.sh](alias.sh) | 💡 Shell 别名 - 便捷命令 |

---

## 项目结构

```
memoryindex/
├── cli/                   # 命令行界面
│   └── search_cli.py     # 搜索命令
├── core/                 # 核心功能
│   ├── process_video.py  # 视频处理
│   ├── video_downloader.py # 视频下载
│   └── db_integration.py # 数据库集成
├── db/                   # 数据库层
│   ├── models.py        # 数据模型
│   ├── repository.py    # 数据访问
│   ├── search.py        # 搜索引擎
│   └── whoosh_search.py # 全文索引
├── ocr/                  # OCR 模块
│   ├── ocr_parallel.py  # 并行处理
│   └── ocr_utils.py     # OCR 工具
├── output/              # 输出目录
├── storage/             # 数据存储
└── videos/              # 视频文件
```

---

## 🚀 快速开始（传统方式）

### ✨ 零配置启动

**首次运行会自动完成所有环境配置！**

```bash
# 1. 确保 ffmpeg 已安装
brew install ffmpeg  # 如果未安装

# 2. 直接开始处理视频（首次运行会自动创建虚拟环境）
make run VIDEO=/path/to/your/video.mp4
```

首次运行会自动：
- ✅ 创建虚拟环境 (`.venv`)
- ✅ 安装所有依赖包
- ✅ 运行环境自检
- ✅ 创建配置文件模板

### 查看所有命令

```bash
make help
```

---

## 手动环境设置（可选）

如果你想手动控制环境配置：

### 1. 确保 ffmpeg 已安装

```bash
ffmpeg -version

# 如果未安装，使用 Homebrew 安装：
brew install ffmpeg
```

### 2. 手动初始化环境

```bash
make setup
```

### 3. 配置 Groq API（可选）

如果需要使用 Groq 的语音转文字和 LLM 总结功能：

```bash
# 1. 复制环境变量模板
cp .env.example .env

# 2. 编辑 .env 文件，填入你的 API Key
nano .env

# 3. 从 https://console.groq.com/keys 获取 API Key
```

详细配置见 [GROQ_SETUP.md](./GROQ_SETUP.md)

## 使用方法（Makefile）

### 🚀 快速开始（推荐使用 Makefile）

#### 本地视频 - 仅音频转文字 + AI 总结（快速）
```bash
make run VIDEO=/path/to/video.mp4
```

#### 本地视频 - 音频 + OCR + AI 总结（完整）
```bash
make ocr VIDEO=/path/to/video.mp4
```

#### 🆕 从 URL 下载并处理 - 仅音频（快速）
```bash
# 直接使用 URL
make download-run URL="https://www.youtube.com/watch?v=xxxxx"

# 或粘贴分享文本（系统自动提取 URL）
make download-run URL="朋友推荐的视频：https://youtu.be/xxxxx 很有趣"
make download-run URL="B站分享 - https://b23.tv/abc - 必看"
```

#### 🆕 从 URL 下载并处理 - 完整 OCR（完整）
```bash
# 直接使用 URL
make download-ocr URL="https://www.bilibili.com/video/BVxxxxx"

# 或粘贴分享文本
make download-ocr URL="这个视频很有趣→ https://b23.tv/xyz ←推荐看看"
```

#### 🆕 仅下载视频（不处理）
```bash
# 使用 Makefile（推荐）
make download URL="https://www.youtube.com/watch?v=xxxxx"

# 强制重新下载
make download URL="https://www.bilibili.com/video/BVxxxxx" FORCE=1

# 或直接使用 process_video.py
python core/process_video.py "https://www.youtube.com/watch?v=xxxxx" --download-only
```

#### 查看所有命令
```bash
make help
```

---

## ✨ URL 智能提取功能详解（新增）

### 什么是 URL 智能提取？

用户可以**直接粘贴任何包含视频链接的文本**（微信分享、QQ 聊天记录等），系统会自动识别和提取有效的 URL，无需手动复制链接。

### 支持的输入格式

| 输入类型 | 示例 | 说明 |
|--------|------|------|
| 纯 URL | `https://www.youtube.com/watch?v=xxx` | 传统用法，仍然支持 |
| 微信分享 | `朋友分享的视频：https://youtu.be/xxx 很有趣` | 直接粘贴分享链接 |
| QQ 聊天记录 | `看这个 https://b23.tv/abc 笑死了` | 支持各种文本格式 |
| 特殊字符 | `推荐→ https://bilibili.com/video/BVxxx ← 超好` | 自动清理尾部符号 |
| 短链接 | `https://b23.tv/abc` 或 `https://youtu.be/xxx` | 自动识别并处理 |

### 支持的视频平台

- ✅ **YouTube** - youtube.com, youtu.be
- ✅ **Bilibili** - bilibili.com, b23.tv
- ✅ **小红书** - xiaohongshu.com, xhslink.com
- ✅ **抖音** - douyin.com
- ✅ **Twitter/X** - twitter.com, x.com
- ✅ **通用** - 其他 http:// 和 https:// URL

### 使用示例

```bash
# 示例 1: 微信分享文本
make download-run URL="分享一个B站视频给你：https://www.bilibili.com/video/BV1ngCyBiEkc?vd_source=... 看看这个"

# 示例 2: QQ 聊天记录
make download-ocr URL="嘿，推荐看这个 https://youtu.be/dQw4w9WgXcQ 超有趣"

# 示例 3: 特殊字符包装
make download-run URL="看！→ https://b23.tv/abc ← 这个视频笑死我了。。。"

# 示例 4: 纯链接（仍然支持）
make download-run URL="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 工作原理

1. **输入识别** - 检查输入文本是否包含视频 URL
2. **URL 提取** - 使用 11 种平台的正则模式匹配和提取
3. **自动清理** - 移除尾部标点符号（。，；等）
4. **平台检测** - 识别视频来源平台
5. **自动下载** - 使用对应平台的下载工具
6. **文件处理** - 继续音频提取、OCR 或 AI 总结

### 自动清理规则

系统会自动移除以下尾部字符，保留有效的 URL：

```
。， ； ： '" ) ]
```

这样即使 URL 后面有标点符号也能被正确提取。

---

## 📥 视频下载层详解

### 多平台统一下载

系统集成了三个强大的下载工具，自动选择最适合的方案：

1. **yt-dlp** （主方案）- 通用下载器，支持 1000+ 网站
2. **BBDown** （Bilibili 降级） - 专门为 B 站优化
3. **XHS-Downloader** （小红书降级） - 专门为小红书优化

### 下载工作流程

```
用户提供 URL（可能带额外文本）
    ↓
自动提取有效的 URL
    ↓
检测视频平台
    ↓
选择最优下载工具（yt-dlp 优先）
    ↓
下载视频到 videos/ 目录
    ↓
自动生成统一格式的文件名
    ↓
继续处理管道（音频/OCR）
```

### 文件命名规范

所有下载的视频都遵循统一的命名格式：

```
标题_平台_视频ID.mp4
```

示例：
- `Never_Gonna_Give_You_Up_youtube_dQw4w9WgXcQ.mp4`
- `INTP：你不是迷茫而是在逃避真正的目标_bilibili_BV1ngCyBiEkc.mp4`

这样做的优势：
- 文件名以标题开头，易于识别内容
- 包含平台标记，便于溯源
- 包含视频 ID，便于快速查找

---

## 🎬 视频处理流程

### 模式对比

| 模式 | 命令 | 处理内容 | 耗时 | 适用场景 |
|------|------|--------|------|--------|
| **快速（音频）** | `make run` | 音频转写 + AI 总结 | ⚡ 快 | 播客、会议、讲座 |
| **完整（OCR）** | `make ocr` | 画面文字 + 音频转写 + AI 总结 | 🐢 慢 | 教学视频、PPT 演示 |
| **下载+快速** | `make download-run` | 下载 + 音频处理 | ⚡⚡ 中等 | 在线视频（音频为主） |
| **下载+完整** | `make download-ocr` | 下载 + 完整处理 | 🐢 慢 | 在线视频（完整分析） |

### 详细处理步骤

#### 音频模式（`make run` 或 `make download-run`）

```
1. 音频提取 - ffmpeg 从视频中提取音频
2. 音频转文字 - Groq Whisper API 进行语音识别
3. AI 总结 - Groq GPT-OSS 120B 生成摘要
4. 报告生成 - 合并转写和摘要结果
```

#### OCR 模式（`make ocr` 或 `make download-ocr`）

```
1. 抽帧 - ffmpeg 从视频提取帧（默认 1fps）
2. OCR 识别 - PaddleOCR 识别画面中的文字
3. 音频提取 - ffmpeg 提取音频
4. 音频转文字 - Groq Whisper API 进行语音识别
5. AI 总结 - Groq GPT-OSS 120B 生成摘要
6. 报告生成 - 合并 OCR、转写和摘要
```

### OCR 模型选择

系统支持选择不同性能级别的 PaddleOCR 模型：

```bash
# 高精度模式（推荐重要内容）
make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server

# 快速模式（推荐日常使用，默认）
make ocr VIDEO=xxx DET_MODEL=mobile REC_MODEL=mobile

# 平衡模式（性价比最高）
make ocr VIDEO=xxx DET_MODEL=mobile REC_MODEL=server
```

性能对比（基于 52 帧测试）：

| 模型配置 | 总耗时 | 单帧耗时 | 识别精度 | 推荐场景 |
|--------|------|--------|--------|--------|
| mobile + mobile | ~90秒 | ~1.7秒 | 85-90% | 清晰内容、快速处理 |
| mobile + server | ~120秒 | ~2.3秒 | 90-95% | 普通视频（默认） |
| server + server | ~180秒 | ~3.5秒 | 95-98% | 重要内容、高精度 |

### ⚡ GPU 加速（新增）

系统支持使用 GPU 加速 OCR 处理，可显著提升性能（约 3-5 倍加速）。

#### 启用 GPU 加速

```bash
# 方式1：使用命令行参数（推荐）
python process_video.py video.mp4 --with-frames --use-gpu

# 方式2：使用双语言OCR工具
python ocr_bilingual.py image.png --gpu

# 方式3：在代码中启用
from ocr_utils import init_ocr
ocr = init_ocr(use_gpu=True)  # 强制使用GPU
```

#### GPU 检测与测试

```bash
# 检测GPU是否可用
python test_gpu.py

# 测试GPU加速性能（需要提供测试图片）
python test_gpu.py image.png

# 对比CPU vs GPU性能
python test_gpu.py image.png --compare
```

#### GPU 环境要求

1. **NVIDIA GPU**：需要支持 CUDA 的显卡
2. **CUDA Toolkit**：需要安装 CUDA（推荐 11.x 或 12.x）
3. **PaddlePaddle GPU版本**：
   ```bash
   # 安装GPU版本的PaddlePaddle（根据CUDA版本选择）
   # CUDA 11.x
   pip install paddlepaddle-gpu==2.6.1 -i https://mirror.baidu.com/pypi/simple
   
   # CUDA 12.x
   pip install paddlepaddle-gpu==2.6.1.post120 -i https://mirror.baidu.com/pypi/simple
   ```

#### 性能对比（GPU vs CPU）

基于典型视频（52帧）的测试结果：

| 模式 | 总耗时 | 加速比 | 说明 |
|------|--------|--------|------|
| CPU (server + server) | ~180秒 | 1.0x | 基准性能 |
| GPU (server + server) | ~40-60秒 | 3-4.5x | 显著提速 |
| CPU (mobile + mobile) | ~90秒 | 1.0x | 轻量模型 |
| GPU (mobile + mobile) | ~20-30秒 | 3-4.5x | 快速处理 |

**注意**：
- GPU 加速效果取决于显卡性能和 CUDA 配置
- 系统会自动检测 GPU 可用性，如果 GPU 不可用会自动降级到 CPU
- 首次运行 GPU 模式时，PaddleOCR 会下载 GPU 优化模型（约 10-30秒）

---

## 🔧 配置与优化

### 环境变量配置

创建 `.env` 文件并填入：

```bash
# Groq API 密钥（必需，从 https://console.groq.com/keys 获取）
GROQ_API_KEY=gsk_xxxxx

# 语音识别模型（可选，默认使用最优）
GROQ_ASR_MODEL=whisper-large-v3-turbo

# 文本总结模型（可选，默认使用 GPT-OSS 120B）
GROQ_LLM_MODEL=openai/gpt-oss-120b

# 输出配置（可选）
GROQ_MAX_TOKENS=4096
GROQ_TEMPERATURE=0.7
```

### 性能优化建议

1. **内存充足** - 使用 server 模型获得最高精度
2. **内存不足** - 使用 mobile 模型保证稳定性
3. **快速处理** - 只处理音频（不启用 OCR）
4. **高质量输出** - 使用 `make ocr` 的完整处理流程
5. **批量处理** - 使用循环批量处理多个文件

```bash
# 批量处理示例
for f in videos/*.mp4; do
  make run VIDEO="$f"
done
```

---

## 📂 输出目录结构

```
output/
├── audio/                      # 提取的音频文件
│   ├── video1.wav
│   ├── video2.wav
│   └── ...
├── frames/                     # 抽取的视频帧（OCR 模式）
│   ├── video1/
│   │   ├── frame_0001.png
│   │   ├── frame_0002.png
│   │   └── ...
│   └── video2/
└── reports/                    # 处理报告
    ├── video1_20251212_180000/
    │   ├── transcript_raw.txt  # 原始语音转写
    │   ├── ocr_raw.txt        # 原始 OCR 识别结果
    │   ├── report.md          # 格式化的最终报告
    │   └── frames/            # 该次处理的帧图像
    └── video2_20251212_181000/
        └── ...
```

---

## 🚀 进阶用法

### 自定义输出目录

```bash
python process_video.py video.mp4 --out-dir /custom/path
```

### 指定 OCR 语言

```bash
# 中文（默认）
make ocr VIDEO=xxx.mp4 OCR_LANG=ch

# 英文
make ocr VIDEO=xxx.mp4 OCR_LANG=en

# 繁体中文
make ocr VIDEO=xxx.mp4 OCR_LANG=chinese_cht
```

### 查看实时日志

```bash
make run VIDEO=xxx.mp4 2>&1 | tee process.log
```

### 检查系统状态

```bash
make check    # 检查虚拟环境、依赖、配置等
make test     # 运行环境测试
```

---

## ❓ 常见问题

### 关于 URL 提取

**Q: 必须是纯 URL 吗？**
A: 不必！支持任何包含 URL 的文本。直接粘贴分享内容即可。

**Q: 可以一次提取多个链接吗？**
A: 目前提取第一个有效的 URL。如需处理多个，请分别执行命令。

**Q: 提取失败时会怎样？**
A: 显示友好的错误提示，列出支持的 URL 格式和输入建议。

**Q: 支持其他平台吗？**
A: 当前支持主流平台（YouTube, B站, 小红书, 抖音, Twitter）。欢迎提出新平台需求！

### 关于视频处理

**Q: `make run` 和 `make ocr` 有什么区别？**
A: `run` 只处理音频（快速），`ocr` 同时处理音频和画面文字（较慢但信息更完整）。

**Q: 为什么首次运行很慢？**
A: 系统在自动下载 PaddleOCR 模型和其他依赖，通常只需一次。后续会很快。

**Q: 可以自定义抽帧频率吗？**
A: 可以修改代码中的 `fps` 参数，或联系开发者添加命令行选项。

**Q: OCR 识别不准确怎么办？**
A: 尝试使用 server 模型：`make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server`

**Q: 处理速度太慢怎么办？**
A: 1) 使用 mobile 模型（默认）2) 只处理音频 3) 减少抽帧频率

**Q: 内存不足怎么办？**
A: 使用 mobile 模型或减少同时处理的文件数量

### 关于环境配置

**Q: GROQ_API_KEY 未设置怎么办？**
A: 编辑 `.env` 文件，从 https://console.groq.com/keys 获取密钥并填入。

**Q: ffmpeg 找不到怎么办？**
A: 运行 `brew install ffmpeg`（macOS）或从官网下载安装。

**Q: 虚拟环境损坏了怎么办？**
A: 运行 `make clean-all` 清理并重建。

---

## 📚 文档导航

| 文档 | 用途 |
|------|------|
| [CHEATSHEET.txt](./CHEATSHEET.txt) | 快速参考卡片，包含所有常用命令 |
| [START.md](./docs/START.md) | 详细启动指南和配置说明 |
| [GROQ_SETUP.md](./docs/GROQ_SETUP.md) | Groq API 配置完全指南 |
| [OCR_MODELS.md](./docs/OCR_MODELS.md) | OCR 模型选择和优化指南 |
| [DOWNLOAD_GUIDE.md](./docs/DOWNLOAD_GUIDE.md) | 视频下载功能完整说明 |
| [URL_EXTRACTION_GUIDE.txt](./docs/URL_EXTRACTION_GUIDE.txt) | URL 智能提取功能详解 |

---

## 💡 Pro Tips

1. **首次使用直接开始** - 无需手动配置环境
   ```bash
   make run VIDEO=video.mp4
   ```

2. **从 URL 一键处理** - 支持多平台自动识别
   ```bash
   make download-ocr URL="https://www.youtube.com/watch?v=xxx"
   ```

3. **粘贴分享内容** - 自动提取链接，无需手动复制
   ```bash
   make download-run URL="朋友分享的视频：链接在这..."
   ```

4. **根据内容选择模式** - 音频为主用 `run`，有文字用 `ocr`

5. **批量处理多个视频**
   ```bash
   for f in *.mp4; do make run VIDEO="$f"; done
   ```

6. **查看实时日志** - 了解处理进度
   ```bash
   make run VIDEO=xxx 2>&1 | tee process.log
   ```

7. **检查系统状态** - 验证所有依赖都正确安装
   ```bash
   make check
   ```

8. **高性能处理** - 在高性能工作站上使用 server 模型
   ```bash
   make ocr VIDEO=xxx DET_MODEL=server REC_MODEL=server
   ```

---

## 🔗 相关链接

- [Groq Console](https://console.groq.com) - 获取和管理 API 密钥
- [Groq API 文档](https://console.groq.com/docs) - API 使用说明
- [yt-dlp 项目](https://github.com/yt-dlp/yt-dlp) - 视频下载工具
- [PaddleOCR 文档](https://github.com/PaddlePaddle/PaddleOCR) - OCR 识别工具

---

## 📊 性能数据（参考）

基于测试视频进行的性能测试：

| 任务 | 耗时 | 备注 |
|------|------|------|
| 仅音频转写（10 分钟视频） | ~30 秒 | 使用 Groq API |
| OCR 处理（52 帧 mobile 模型） | ~90 秒 | 单帧 ~1.7 秒 |
| OCR 处理（52 帧 server 模型） | ~180 秒 | 单帧 ~3.5 秒 |
| AI 摘要生成（3000 字） | ~5 秒 | 使用 GPT-OSS 120B |
| 完整处理（音频 + OCR + 摘要） | ~3-5 分钟 | 取决于视频长度和模型选择 |

---

## 🎯 项目进度

### ✅ 已完成
- 统一视频下载层（支持多平台）
- 智能 URL 提取（从分享文本自动识别链接）
- 自动化虚拟环境管理
- 多模式视频处理（音频 + OCR）
- PaddleOCR 集成和优化
- Groq API 集成（ASR + LLM）
- 完整的命令行工具和 Makefile
- 综合文档和快速参考

### 🚀 即将推出
- 支持更多视频平台
- 视频摘要的视觉化展示
- 报告搜索和存档系统
- 批量处理界面
- 图形化配置工具

---

## 📝 许可证

MIT License - 开源免费使用

---

**最后更新**：2025-12-12  
**版本**：v2.1 - 统一下载层 + 智能 URL 提取 + 自动化环境  
**状态**：✅ 生产就绪
```

**详细启动指南见：[START.md](./START.md)**

---

### 传统方式（手动激活环境）

#### 基础用法 - 只处理音频

```bash
cd /Users/catherina/Documents/GitHub/knowledge/video_report
source .venv/bin/activate

python process_video.py /path/to/video.mp4
```

**输出**：
- `output/audio/` - 分离的音频 WAV 文件
- `output/reports/` - 处理报告（包含转写结果和 AI 总结）

#### 高级用法 - 启用抽帧 + OCR

```bash
python process_video.py /path/to/video.mp4 --with-frames
```

**输出**：
- `output/audio/` - 分离的音频 WAV 文件
- `output/frames/` - 提取的帧图像（PNG 格式）
- `output/reports/` - 包含 OCR 文字识别结果的报告

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `video` | 视频文件路径（必须） | `/path/to/video.mp4` |
| `--with-frames` | 启用抽帧 + OCR | 不需要赋值 |
| `--out-dir` | 输出目录（默认：`./output`） | `--out-dir /custom/path` |
| `--ocr-lang` | PaddleOCR 语言（默认：`ch`） | `--ocr-lang en` |

#### 语言选项

- `ch` - 中文简体
- `en` - English
- `chinese_cht` - 繁体中文
- 其他更多语言见 PaddleOCR 文档

## 核心模块说明

### `process_video.py`

主控制脚本，负责：
1. 命令行参数解析
2. 创建输出目录
3. 调度音频提取 → 抽帧 → OCR → 报告生成

**关键函数**：
- `extract_audio()` - ffmpeg 音频分离
- `extract_frames()` - ffmpeg 抽帧（默认 1 fps）
- `transcribe_audio_with_groq()` - **【待填充】** Groq 语音转文字
- `summarize_with_gpt_oss_120b()` - **【待填充】** Groq 摘要功能

### `ocr_utils.py`

OCR 工具库，提供：
- `init_ocr(lang)` - 初始化 PaddleOCR 模型
- `ocr_image(ocr, image_path)` - 单张图片 OCR 识别
- `ocr_folder_to_text(ocr, frames_dir)` - 批量处理整个目录

**可信度过滤**：默认只保留识别分数 ≥ 0.5 的文字

## 下一步计划

- [ ] 集成 Groq ASR API（语音转文字）
- [ ] 集成 Groq GPT-OSS 120B（文本总结）
- [ ] 关键帧截图自动插入报告
- [ ] 报告存档 + 搜索系统（SQLite / Vector DB）
- [ ] 支持更多视频格式和抽帧参数调整

## 故障排查

### PaddleOCR 模型下载缓慢

第一次运行时，PaddleOCR 会自动下载模型文件，可能较慢。可以设置环境变量跳过源检查：

```bash
DISABLE_MODEL_SOURCE_CHECK=True python process_video.py ...
```

### ffmpeg 找不到

确保已安装并在 PATH 中：

```bash
which ffmpeg
# 应该输出类似：/usr/local/bin/ffmpeg
```

## 依赖版本信息

- Python 3.7+
- PaddleOCR 3.3.2
- PaddlePaddle 3.2.2
- OpenCV 4.12.0
- NumPy 2.2.6
- FFmpeg 7.1+（系统级，非 Python 包）
