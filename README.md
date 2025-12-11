# Video → Text Report Pipeline

一个本地视频处理骨架项目，支持：
- 🎬 **抽帧** - 使用 ffmpeg 从视频提取帧
- 🗣️ **音频分离** - 提取视频中的音频并转换为 WAV 格式  
- 🔤 **本地 OCR** - 使用 PaddleOCR 对提取的帧进行文字识别
- 📝 **报告生成** - 合并音频转写和 OCR 结果，生成最终报告

> Groq API 集成（语音转文字 + GPT-OSS 120B 总结）暂时留接口占位，待后续填充

## 项目结构

```
video_report/
├── process_video.py       # 主入口脚本
├── ocr_utils.py          # OCR 工具库
├── requirements.txt      # Python 依赖
├── output/               # 输出目录（自动生成）
│   ├── audio/           # 提取的音频文件
│   ├── frames/          # 抽取的帧图像
│   └── reports/         # 生成的报告
└── .venv/               # Python 虚拟环境
```

## 🚀 快速开始（全新自动化）

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

## 使用方法

### 🚀 快速开始（推荐使用 Makefile）

#### 方式 1：仅音频转文字 + AI 总结（快速）
```bash
make run VIDEO=/path/to/video.mp4
```

#### 方式 2：音频 + OCR + AI 总结（完整）
```bash
make ocr VIDEO=/path/to/video.mp4
```

#### 查看所有命令
```bash
make help
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
