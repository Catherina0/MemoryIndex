# config_example.py
"""
配置文件示例
这个文件展示了如何为项目添加配置参数

使用方法：
1. 复制这个文件为 config.py
2. 根据需要修改参数
3. 在 process_video.py 中导入：from config import *
"""

# ========== 输出目录配置 ==========
OUTPUT_DIR = "output"
AUDIO_DIR = f"{OUTPUT_DIR}/audio"
FRAMES_DIR = f"{OUTPUT_DIR}/frames"
REPORTS_DIR = f"{OUTPUT_DIR}/reports"

# ========== 抽帧配置 ==========
# FPS：每秒抽取多少帧（1 = 每秒 1 帧，2 = 每秒 2 帧...）
FRAME_EXTRACTION_FPS = 1

# 帧图片格式
FRAME_FORMAT = "png"

# ========== OCR 配置 ==========
# 语言：'ch'(中文), 'en'(英文), 'chinese_cht'(繁体中文)
OCR_LANGUAGE = "ch"

# 文本信度过滤阈值（0.0-1.0）
# 只保留识别分数 >= 此值的文字
OCR_CONFIDENCE_THRESHOLD = 0.5

# 是否使用 GPU（如果可用）
OCR_USE_GPU = False

# ========== 音频配置 ==========
# 采样率（Hz）
AUDIO_SAMPLE_RATE = 16000

# 音频声道数
AUDIO_CHANNELS = 1

# 音频编码格式
AUDIO_CODEC = "pcm_s16le"

# ========== Groq API 配置 ==========
# 这些是占位符，后续集成 Groq 时使用
GROQ_API_KEY = ""  # TODO: 从环境变量或密钥管理器读取
GROQ_ASR_MODEL = "whisper-large-v3-turbo"
GROQ_LLM_MODEL = "mixtral-8x7b-32768"  # 或其他 Groq 支持的模型
GROQ_NAMING_MODEL = "llama-3.1-8b-instant"  # 专门用于命名的模型
GROQ_NAMING_MODEL = "openai/gpt-oss-20b"  # 专门用于命名的模型

# 摘要 prompt 模板
SUMMARY_PROMPT_TEMPLATE = """
请根据以下文字内容进行总结：

内容:
{text}

要求：
1. 提取核心要点
2. 保留重要数字和引用
3. 尽可能详细的输出内容
"""

# ========== 调试配置 ==========
DEBUG = False
VERBOSE = False

# 跳过 PaddleOCR 的模型源检查（加速启动）
DISABLE_OCR_SOURCE_CHECK = False

# ========== 日志配置 ==========
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "[%(levelname)s] %(message)s"
