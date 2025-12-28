# 项目快速启动指南

## ✨ 全新：自动化启动（推荐）

**首次运行任何命令时会自动完成所有环境配置！**

```bash
# 1. 进入项目目录
cd /Users/catherina/Documents/GitHub/knowledge

# 2. 直接开始处理视频（首次运行会自动创建虚拟环境）
make run VIDEO=/path/to/your/video.mp4
```

这将自动：
- ✅ 创建虚拟环境 (`.venv`)
- ✅ 安装所有依赖包
- ✅ 运行环境自检
- ✅ 处理你的视频

## 传统方式（可选）

如果你想手动控制：

```bash
# 1. 手动初始化环境
make setup

# 2. 运行环境测试
make test

# 3. 处理视频
make run VIDEO=/path/to/your/video.mp4
```

## 测试流程

### 场景 1️⃣：只提取音频（推荐先跑这个）

如果你有一个测试视频，比如 `~/test.mp4`：

```bash
python process_video.py ~/test.mp4
```

**预期输出**：
```
>> 提取音频中...
>> 调用 Groq 语音转写（占位）...
>> 调用 GPT-OSS 120B 做总结（占位）...
>> 报告已保存到: output/reports/test_report.txt
```

### 场景 2️⃣：启用抽帧 + OCR

```bash
python process_video.py ~/test.mp4 --with-frames
```

**预期输出**：
```
>> 提取音频中...
>> 调用 Groq 语音转写（占位）...
>> 抽帧中...
>> 初始化本地 OCR...
>> 对所有帧做 OCR...
>> 调用 GPT-OSS 120B 做总结（占位）...
>> 报告已保存到: output/reports/test_report.txt
```

## 关键文件说明

| 文件 | 用途 |
|------|------|
| `process_video.py` | 主程序入口 |
| `ocr_utils.py` | OCR 工具集 |
| `requirements.txt` | Python 依赖列表 |
| `output/` | 输出文件夹（自动生成） |

## 调试技巧

### 查看具体的 ffmpeg 命令

修改 `process_video.py` 中的 `subprocess.run()` 调用为 `print()` 可以看到实际执行的命令。

### 临时禁用 OCR 下载检查

```bash
DISABLE_MODEL_SOURCE_CHECK=True python process_video.py ~/test.mp4 --with-frames
```

### 指定不同的 OCR 语言

```bash
# 英文识别
python process_video.py ~/test.mp4 --with-frames --ocr-lang en

# 繁体中文
python process_video.py ~/test.mp4 --with-frames --ocr-lang chinese_cht
```

## 项目状态

- ✅ 本地骨架完成
- ✅ ffmpeg 集成（音频 + 抽帧）
- ✅ PaddleOCR 集成
- ⏳ Groq API 接口（占位，待填充）
  - `transcribe_audio_with_groq()` - 位置：`process_video.py` 第 57 行
  - `summarize_with_gpt_oss_120b()` - 位置：`process_video.py` 第 68 行

## 下一步

当你准备好集成 Groq API 时，更新这两个函数：

```python
# process_video.py

def transcribe_audio_with_groq(audio_path: Path) -> str:
    """用 Groq ASR 模型转写音频"""
    # TODO: 
    # 1. 初始化 Groq 客户端（使用 API key）
    # 2. 读取 audio_path 的二进制内容
    # 3. 调用 Groq 语音转文字接口
    # 4. 返回转写文本
    pass

def summarize_with_gpt_oss_120b(full_text: str) -> str:
    """用 Groq 的 GPT-OSS 120B 做总结"""
    # TODO:
    # 1. 初始化 Groq 客户端
    # 2. 构造 prompt，将 full_text 作为输入
    # 3. 调用 GPT-OSS 120B 模型
    # 4. 返回总结文本
    pass
```

有问题时，检查这些可能的原因：

- 🔗 ffmpeg 未安装或不在 PATH
- 📦 虚拟环境未激活（`.venv` 中找不到依赖）
- 🎥 视频文件格式不支持（最好用 MP4）
- 📥 PaddleOCR 模型第一次下载较慢

祝你使用愉快！🎉
