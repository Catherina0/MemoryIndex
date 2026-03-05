# process_video.py
import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from google import genai
import re
import json
import warnings
import logging

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 抑制 PaddleOCR/PaddleX 模型加载日志（必须在 import 前设置）
os.environ['PADDLEX_DISABLE_PRINT'] = '1'
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
warnings.filterwarnings('ignore')
logging.getLogger('ppocr').setLevel(logging.ERROR)
logging.getLogger('paddle').setLevel(logging.ERROR)
logging.getLogger('paddlex').setLevel(logging.ERROR)

# OCR 引擎选择：优先使用 Vision OCR（macOS），否则使用 PaddleOCR
import platform
OCR_ENGINE = None  # 'vision' 或 'paddle'

# 尝试导入 Vision OCR（macOS）
try:
    from ocr.ocr_vision import init_vision_ocr, ocr_folder_vision
    if platform.system() == 'Darwin':  # macOS
        OCR_ENGINE = 'vision'
        print("✅ 使用 Apple Vision OCR（系统原生）")
except ImportError:
    init_vision_ocr = None
    ocr_folder_vision = None

# 如果 Vision OCR 不可用，尝试导入 PaddleOCR
if not OCR_ENGINE:
    try:
        from ocr.ocr_utils import init_ocr, ocr_folder_to_text
        OCR_ENGINE = 'paddle'
        print("✅ 使用 PaddleOCR")
    except ImportError:
        init_ocr = None
        ocr_folder_to_text = None
        print("⚠️  警告：未找到可用的 OCR 引擎")
        print("   • macOS: 无需安装，应该自动检测 Vision OCR")
        print("   • 其他平台: 请运行 'make install-paddle-ocr'")
else:
    # 即使选择了 Vision OCR，也许可以作为备用加载 PaddleOCR
    # 但为了简单，如果 vision 选定，我们在此处不强制加载 paddle
    # 但是为了避免后续 UnboundLocalError，我们在这里尝试导入 paddle (如果不导入，init_ocr 会是 unbound)
    try:
        from ocr.ocr_utils import init_ocr, ocr_folder_to_text
    except ImportError:
        init_ocr = None
        ocr_folder_to_text = None

# 导入多进程OCR（用于提升CPU利用率）
try:
    from ocr.ocr_parallel import ocr_folder_parallel
    PARALLEL_OCR_AVAILABLE = True
except ImportError:
    PARALLEL_OCR_AVAILABLE = False
    print("⚠️  多进程OCR模块不可用，将使用单进程模式")

# 导入智能抽帧（新增）
try:
    from core.smart_frame_extractor import SmartFrameExtractor
    SMART_EXTRACT_AVAILABLE = True
except ImportError:
    SMART_EXTRACT_AVAILABLE = False
    print("⚠️  智能抽帧模块加载失败")

# 导入数据库模块
from db import VideoRepository
from db.models import Video, Artifact, Topic, TimelineEntry, SourceType, ArtifactType, ProcessingStatus

# 可选：支持从 URL 直接下载
try:
    from core.video_downloader import VideoDownloader
    DOWNLOADER_AVAILABLE = True
except ImportError:
    DOWNLOADER_AVAILABLE = False

# 加载环境变量
load_dotenv()


# 尝试从 core 导入大图分割工具
try:
    from core.image_utils import split_long_image
except ImportError:
    split_long_image = None
    print("⚠️  Warning: split_long_image utility not found")

# ========== 路径/目录处理 ==========
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


# ========== ffmpeg: 音频 & 抽帧 ==========

# Groq Whisper API 限制
MAX_AUDIO_SIZE_MB = 20
MAX_AUDIO_SIZE_BYTES = MAX_AUDIO_SIZE_MB * 1024 * 1024

def get_video_duration(video_path: Path) -> float:
    """
    使用 ffprobe 获取视频时长（秒）。
    
    Returns:
        float: 视频时长（秒），如果获取失败返回 0
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"⚠️  警告：无法获取视频时长: {e}")
        return 0


def extract_audio(video_path: Path, audio_path: Path):
    """
    用 ffmpeg 从视频里分离音频，输出为压缩的 wav。
    使用以下参数压缩音频：
      - ac 1: 单声道
      - ar 16000: 采样率 16kHz
      - sample_fmt s16: 16-bit PCM
    """
    ensure_dir(audio_path.parent)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",                    # no video
        "-acodec", "pcm_s16le",   # 16-bit PCM
        "-ar", "16000",           # 采样率 16kHz
        "-ac", "1",               # 单声道
        str(audio_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def get_audio_duration(audio_path: Path) -> float:
    """
    使用 ffprobe 获取音频时长（秒）。
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0


def split_audio(audio_path: Path, max_size_mb: float = MAX_AUDIO_SIZE_MB) -> list:
    """
    如果音频文件超过指定大小，拆分成多个片段。
    
    Args:
        audio_path: 音频文件路径
        max_size_mb: 最大文件大小（MB）
    
    Returns:
        list: [(chunk_path, start_time), ...] 每个片段的路径和起始时间（秒）
    """
    file_size = audio_path.stat().st_size
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size <= max_size_bytes:
        return [(audio_path, 0.0)]
    
    # 计算需要拆分的段数
    num_chunks = int(file_size / max_size_bytes) + 1
    duration = get_audio_duration(audio_path)
    
    if duration <= 0:
        print(f"   ⚠️  无法获取音频时长，尝试直接上传")
        return [(audio_path, 0.0)]
    
    chunk_duration = duration / num_chunks
    
    print(f"   📊 音频文件: {file_size / 1024 / 1024:.1f}MB > {max_size_mb}MB")
    print(f"   ✂️  拆分为 {num_chunks} 段 (每段约 {chunk_duration:.0f}秒)")
    
    chunks = []
    chunk_dir = audio_path.parent / "audio_chunks"
    ensure_dir(chunk_dir)
    
    for i in range(num_chunks):
        start_time = i * chunk_duration
        chunk_path = chunk_dir / f"chunk_{i:03d}.wav"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(audio_path),
            "-ss", str(start_time),
            "-t", str(chunk_duration),
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(chunk_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        chunks.append((chunk_path, start_time))
        print(f"   ✅ 片段 {i+1}/{num_chunks}: {chunk_path.name}")
    
    return chunks



def extract_frames(video_path: Path, frames_dir: Path, fps: int = 1):
    """
    用 ffmpeg 抽帧：默认 1 fps（每秒一帧）。
    帧编号从 1 开始，frame_00001.png 对应第 0-1 秒。
    """
    ensure_dir(frames_dir)
    out_pattern = frames_dir / "frame_%05d.png"
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",  # 只显示错误
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        str(out_pattern),
    ]
    subprocess.run(cmd, check=True)


def match_audio_with_frames(transcript_data: dict, frames_dir: Path, fps: float = 1, duration: float = 0) -> list:
    """
    音画匹配：将音频转写片段与视频帧关联。
    支持稀疏抽帧（Smart Extract）和连续抽帧。
    
    Args:
        transcript_data: 包含 segments 的转写数据
        frames_dir: 视频帧目录
        fps: 抽帧频率（每秒帧数）
        duration: 视频总时长（秒），用于确定最后一帧的结束时间
    
    Returns:
        list: [{'second': 0, 'frame': 'frame_00001.png', 'text': '对应的文本'}, ...]
    """
    import glob
    
    # 获取所有帧文件
    # 支持 frame_XXXXX.png (普通模式) 和 keyframe_XXXXXXXX.png (智能模式)
    frame_files_all = sorted(glob.glob(str(frames_dir / "*.png")))
    # 过滤掉非预期文件
    frame_files = [f for f in frame_files_all if "frame_" in Path(f).name or "keyframe_" in Path(f).name]
    
    if not frame_files:
        return []
    
    timeline = []
    
    # 构建帧的时间段：(filename, start_time, end_time)
    intervals = []
    
    # 预编译正则
    re_legacy = re.compile(r"frame_(\d+)")
    re_smart = re.compile(r"keyframe_(\d+)")
    
    for i in range(len(frame_files)):
        fname = Path(frame_files[i]).name
        
        t_start = 0.0
        
        # 尝试解析智能模式 (keyframe_毫秒)
        match_smart = re_smart.search(fname)
        if match_smart:
            t_start = int(match_smart.group(1)) / 1000.0
        else:
            # 尝试解析普通模式 (frame_序号)
            match_legacy = re_legacy.search(fname)
            if match_legacy:
                idx = int(match_legacy.group(1))
                t_start = (idx - 1) / fps
        
        # 确定结束时间 (下一帧的开始时间)
        if i < len(frame_files) - 1:
            next_fname = Path(frame_files[i+1]).name
            t_end = t_start + 1.0 # 默认 fallback
            
            # 解析下一帧
            match_smart_next = re_smart.search(next_fname)
            if match_smart_next:
                 t_end = int(match_smart_next.group(1)) / 1000.0
            else:
                 match_legacy_next = re_legacy.search(next_fname)
                 if match_legacy_next:
                     idx_next = int(match_legacy_next.group(1))
                     t_end = (idx_next - 1) / fps
        else:
            # 最后一帧
            t_end = duration if duration > 0 else t_start + 5.0
        
        # 修正：如果 t_end < t_start (比如排序乱了)，强制调整
        if t_end < t_start: t_end = t_start + 2.0
            
        intervals.append((fname, t_start, t_end))

    # 为每一帧查找对应的文本
    for fname, start, end in intervals:
        texts_in_interval = []
        if 'segments' in transcript_data:
            for seg in transcript_data['segments']:
                seg_s = seg['start']
                seg_e = seg['end']
                
                # 判断重叠: max(start, seg_s) < min(end, seg_e)
                # 且重叠长度超过一定阈值? 或者只要有重叠?
                # 简单起见：只要有重叠
                if max(start, seg_s) < min(end, seg_e):
                    texts_in_interval.append(seg['text'].strip())
        
        # 去重并拼接
        # texts_in_interval might have duplicates if segment spans multiple frames? 
        # No, we just append content.
        
        unique_texts = []
        seen = set()
        for t in texts_in_interval:
            if t not in seen:
                unique_texts.append(t)
                seen.add(t)
        
        timeline.append({
            'second': int(start), # 兼容旧字段
            'timestamp': start,
            'duration': end - start,
            'frame': fname,
            'text': ' '.join(unique_texts)
        })
    
    return timeline


# ========== Groq API 集成 ==========
def _transcribe_single_audio(client, model_name: str, audio_path: Path) -> dict:
    """
    转写单个音频文件（内部函数）。
    """
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(audio_path.name, audio_file.read()),
            model=model_name,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    
    result = {
        'text': transcription.text,
        'segments': []
    }
    
    if hasattr(transcription, 'segments') and transcription.segments:
        for seg in transcription.segments:
            result['segments'].append({
                'start': seg.get('start', 0),
                'end': seg.get('end', 0),
                'text': seg.get('text', '')
            })
    
    return result


def transcribe_audio_with_groq(audio_path: Path) -> dict:
    """
    使用 Groq 的 Whisper 模型进行语音转文字，返回带时间戳的数据。
    如果音频文件超过 20MB，自动拆分成多段分别识别，然后拼接结果。
    
    Returns:
        dict: {
            'text': '完整文本',
            'segments': [{'start': 0.0, 'end': 2.5, 'text': '片段文本'}, ...]
        }
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，使用占位符")
        return {
            'text': f"[FAKE TRANSCRIPT for {audio_path.name}] 请在 .env 中设置 GROQ_API_KEY",
            'segments': []
        }
    
    try:
        client = Groq(api_key=api_key)
        
        # 确定 ASR 模型
        asr_type = os.getenv("ASR_MODEL_TYPE", "").lower()
        if asr_type == "v3":
            model = "whisper-large-v3"
            print("  🎤 使用模型: Whisper Large V3")
        elif asr_type == "turbo":
            model = "whisper-large-v3-turbo"
            print("  🎤 使用模型: Whisper Large V3 Turbo")
        else:
            # 默认 fallback 到环境变量配置
            model = os.getenv("GROQ_ASR_MODEL", "whisper-large-v3")
        
        # 检查文件大小，决定是否需要拆分
        file_size = audio_path.stat().st_size
        
        if file_size <= MAX_AUDIO_SIZE_BYTES:
            # 文件足够小，直接转写
            result = _transcribe_single_audio(client, model, audio_path)
            result['asr_model'] = model
            return result
        
        # 文件过大，需要拆分
        chunks = split_audio(audio_path)
        
        if len(chunks) == 1:
            # 拆分失败或不需要拆分，尝试直接上传
            result = _transcribe_single_audio(client, model, audio_path)
            result['asr_model'] = model
            return result
        
        # 分段转写并合并结果
        all_text = []
        all_segments = []
        
        for i, (chunk_path, time_offset) in enumerate(chunks):
            print(f"   🎤 转写片段 {i+1}/{len(chunks)}...")
            try:
                chunk_result = _transcribe_single_audio(client, model, chunk_path)
                
                # 添加文本
                if chunk_result.get('text'):
                    all_text.append(chunk_result['text'])
                
                # 添加片段（调整时间偏移）
                for seg in chunk_result.get('segments', []):
                    all_segments.append({
                        'start': seg['start'] + time_offset,
                        'end': seg['end'] + time_offset,
                        'text': seg['text']
                    })
                    
            except Exception as chunk_err:
                print(f"   ⚠️  片段 {i+1} 转写失败: {chunk_err}")
                all_text.append(f"[片段{i+1}转写失败]")
        
        # 清理临时文件
        chunk_dir = audio_path.parent / "audio_chunks"
        if chunk_dir.exists():
            import shutil
            shutil.rmtree(chunk_dir)
        
        print(f"   ✅ 合并 {len(chunks)} 个片段的转写结果")
        
        return {
            'text': ' '.join(all_text),
            'segments': all_segments,
            'asr_model': model
        }
        
    except Exception as e:
        print(f"  ✗ Groq 转写失败: {e}")
        return {
            'text': f"[转写失败: {str(e)}]",
            'segments': [],
            'asr_model': f"{model} (失败)"
        }


def estimate_token_count(text: str) -> int:
    """
    估算文本的 token 数量
    规则：
    - 中文字符：1:1 (1个字符 = 1 token)
    - 其他字符（主要是英文）：2:1 (2个字符 = 1 token，即 count / 2)
    """
    import re
    # 统计中文字符数 (基本汉字范围)
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
    # 统计其他字符数
    other_chars = len(text) - chinese_chars
    
    # 计算 token
    token_count = chinese_chars + int(other_chars / 2)
    return token_count


def summarize_with_gemini(full_text: str, custom_prompt: str = None) -> tuple:
    """
    使用 Gemini API 处理文本
    Args:
        full_text: 输入文本
        custom_prompt: 可选的自定义提示词。如果未提供，使用默认的"知识档案"提示词。
    
    Returns: 
        (summary_text, model_name)
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY 未设置，无法处理长文本")
        return (f"[ERROR: GEMINI_API_KEY 未设置]\n\n{full_text[:1000]}...(文本过长已截断)", f"{model_name} (失败)")
    
    try:
        client = genai.Client(api_key=api_key)
        
        # 如果提供了自定义提示词，直接使用它
        if custom_prompt:
            prompt = f"{custom_prompt}\n\n以下是内容：\n{full_text}"
        else:
            # 默认提示词（生成的摘要/知识档案）
            prompt = f"""

请将以下"带时间戳的音频转写 + OCR 文本"整理成一份**结构化 Markdown 知识档案和内容概要**。


**⚠️ 重要：识别错误修正**
- 语音识别(ASR)和OCR都可能存在**同音字/词的识别错误**，特别是专业术语
- 你必须根据上下文**主动识别并修正**这些错误
- 常见错误类型：
  * 专业术语："机器学习"被识别为"鸡器学习"、"神经网络"识别为"神经往罗"
  * 人名地名："张三"识别为"章三"、"北京"识别为"背景"
  * 英文术语："API"识别为"哎批爱"、"Python"识别为"派森"
  * 数字单位："3千克"识别为"3千客"、"2米"识别为"2密"
- 修正时请使用专业、准确的术语

**⚠️ 内容清洗：忽略广告干扰**
- 请识别并**完全忽略**视频中的插播广告、赞助商口播或跑马灯信息
- 典型例子：转转二手机、拼多多、某某科技企业宣传、"点击关注"、"一键三连"等
- 确保输出内容仅关于视频的核心主题知识，不要包含任何推广信息

你需要：
1. **使用 Markdown** 输出（标题、列表、引用、表格等）
2. 按时间顺序梳理主要片段，并为关键内容标注对应时间戳
3. 合并音频与 OCR 内容：  
   - 如果 OCR 文字不完整，请根据上下文**推断合理含义**  
   - 如果某些屏幕文字重要（如 PPT、界面按钮、参数、代码），请单独提取并解释
   - **不要编造不存在的OCR信息**：如果无法确认屏幕上有具体文字，请不要在"OCR信息与推断"中强行编造。仅在确有依据（时间戳对应的OCR文本）时才列出。
   - **主动修正识别错误**：同音字替换、术语纠正、拼写修复
4. 自动识别"主题/章节"并结构化总结：概念、步骤、场景、结论
5. 提取重要数据：数字、阈值、规则、引用、命令、日期等
6. 生成标签和摘要：
   - **标签（tags）**：3-6个高度概括的主题标签，如"情感"、"告白"、"人生意义"、"科技"、"教育"等。避免使用"语音转写"、"OCR推断"等技术性描述词。标签应简短（1-4个字），概括性强，便于数据库搜索。
   - **摘要**：不超过50个字的系统性内容概括，提炼核心主题和要点。
7. 稍微详细一些，但不要写废话（重点是**可回溯、可搜索、可理解**）

推荐结构：
## 摘要
（不超过50字的核心内容概括）

## 主要内容概括
## 主题总结（自动生成主题名）
## 详细说明（合并音频与 OCR）
## 关键信息（数字、规则、参数）
## OCR 信息与推断（仅列出确凿的屏幕关键文字，不要编造）
## 时间线（关键片段 + 时间戳）
## 关键句（含时间戳）
## 标签
格式：标签: 标签1, 标签2, 标签3

以下是内容：
{full_text}

"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        
        return (response.text, model_name)
    except Exception as e:
        print(f"  ✗ Gemini 总结失败: {e}")
        return (f"[总结失败: {str(e)}]\n\n原始内容:\n{full_text[:1000]}...(已截断)", f"{model_name} (失败)")


def summarize_with_gpt_oss_120b(full_text: str) -> tuple:
    """
    使用 Groq 的 LLM 进行文本总结。
    支持自动切换或强制使用 Gemini。
    返回: (summary_text, model_name)
    """
    # 检查是否强制使用 Gemini
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    if llm_provider == "gemini":
        print("  🔄 用户强制选择: 使用 Gemini API")
        return summarize_with_gemini(full_text)

    # 估算 token 数量
    estimated_tokens = estimate_token_count(full_text)
    print(f"  📊 估算文本长度: ~{estimated_tokens:,} tokens ({len(full_text):,} 字符)")
    
    # 如果超过 5 万 token，使用 Gemini (且没强制指定 oss)
    if estimated_tokens > 50000 and llm_provider != "oss":
        print(f"  🔄 文本过长 (>{50000:,} tokens)，切换到 Gemini API")
        return summarize_with_gemini(full_text)
    
    # 否则使用 Groq
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
    
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，返回原文")
        return (f"[FAKE SUMMARY - 请在 .env 中设置 GROQ_API_KEY]\n\n{full_text}", f"{model_name} (失败)")
    
    try:
        client = Groq(api_key=api_key)
        # 增加 token 限制以支持更长的输出
        max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "8192"))  # 从 4096 提升到 8192
        temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
        
        prompt = f"""

请将以下“带时间戳的音频转写 + OCR 文本”整理成一份**结构化 Markdown 知识档案和内容概要**。


**⚠️ 重要：识别错误修正**
- 语音识别(ASR)和OCR都可能存在**同音字/词的识别错误**，特别是专业术语
- 你必须根据上下文**主动识别并修正**这些错误
- 常见错误类型：
  * 专业术语："机器学习"被识别为"鸡器学习"、"神经网络"识别为"神经往罗"
  * 人名地名："张三"识别为"章三"、"北京"识别为"背景"
  * 英文术语："API"识别为"哎批爱"、"Python"识别为"派森"
  * 数字单位："3千克"识别为"3千客"、"2米"识别为"2密"
- 修正时请使用专业、准确的术语

**⚠️ 内容清洗：忽略广告干扰**
- 请识别并**完全忽略**视频中的插播广告、赞助商口播或跑马灯信息
- 典型例子：转转二手机、拼多多、某某科技企业宣传、"点击关注"、"一键三连"等
- 确保输出内容仅关于视频的核心主题知识

你需要：
1. **使用 Markdown** 输出（标题、列表、引用、表格等）
2. 按时间顺序梳理主要片段，并为关键内容标注对应时间戳
3. 合并音频与 OCR 内容：  
   - 如果 OCR 文字不完整，请根据上下文**推断合理含义**  
   - 如果某些屏幕文字重要（如 PPT、界面按钮、参数、代码），请单独提取并解释
   - **不要编造不存在的OCR信息**：如果无法确认屏幕上有具体文字，请不要在"OCR信息与推断"中强行编造。仅在确有依据（时间戳对应的OCR文本）时才列出。
   - **主动修正识别错误**：同音字替换、术语纠正、拼写修复
4. 自动识别“主题/章节”并结构化总结：概念、步骤、场景、结论
5. 提取重要数据：数字、阈值、规则、引用、命令、日期等
6. 生成标签和摘要：
   - **标签（tags）**：3-6个高度概括的主题标签，如"情感"、"告白"、"人生意义"、"科技"、"教育"等。避免使用"语音转写"、"OCR推断"等技术性描述词。标签应简短（1-4个字），概括性强，便于数据库搜索。
   - **摘要**：不超过50个字的系统性内容概括，提炼核心主题和要点。
7. 稍微详细一些，但不要写废话（重点是**可回溯、可搜索、可理解**）

推荐结构：
## 摘要
（不超过50字的核心内容概括）

## 主要内容概括
## 主题总结（自动生成主题名）
## 详细说明（合并音频与 OCR）
## 关键信息（数字、规则、参数）
## OCR 信息与推断（仅列出确凿的屏幕关键文字，不要编造）
## 时间线（关键片段 + 时间戳）
## 关键句（含时间戳）
## 标签
格式：标签: 标签1, 标签2, 标签3

以下是内容：
{full_text}  



"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个多模态知识档案生成器，具备智能纠错能力。

                    输入来自同一段视频，包括：
                    - 带时间戳的音频转写（可能含ASR识别错误）
                    - 带时间戳或帧序列的 OCR 文本（可能含OCR识别错误）

                    你的职责是：
                    - 融合音频与 OCR 内容
                    - 利用时间戳重建结构与顺序
                    - 根据内容自动识别主题与重点
                    - **智能纠错**：主动识别并修正同音字/词错误，特别是专业术语、人名地名、英文缩写
                    - 推断纠正 OCR 可能的文字识别错误
                    - 确保输出使用准确、专业的术语表达
                    - 生成清晰、可长期保存、适合检索的 Markdown 知识档案"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return (response.choices[0].message.content, model_name)
    except Exception as e:
        print(f"  ✗ Groq 总结失败: {e}")
        return (f"[总结失败: {str(e)}]\n\n原始内容:\n{full_text}", f"{model_name} (失败)")


def generate_detailed_content(full_text: str) -> tuple:
    """
    生成详细的内容概括，包含更多细节。
    支持自动切换或强制使用 Gemini。
    返回: (detailed_content, model_name)
    """
    # 构造 OSS (Groq) 和一般情况的详细内容提示词
    default_prompt_text = f"""
请基于以下视频的音频转写和OCR文本(如果有），生成一份**详细的内容概括**。

**⚠️ 识别错误修正**：
- 音频转写和OCR文本可能存在同音字/词识别错误
- 请根据上下文**主动修正**这些错误，特别是：
  * 专业术语（技术名词、学术概念）
  * 人名、地名、机构名
  * 英文缩写和术语
  * 数字、单位、参数
- 修正后使用准确、规范的表达

**⚠️ 内容清洗：忽略广告干扰**
- 请识别并**完全忽略**视频中的插播广告、赞助商口播或跑马灯信息
- 典型例子：转转二手机、拼多多、某某科技企业宣传、"点击关注"、"一键三连"等
- 确保输出内容仅关于视频的核心主题知识

要求：
1. **逐段详细展开**：按视频的时间顺序，详细描述每个主要部分的内容
2. **保留关键细节**：
   - 具体的数字、数据、参数（修正识别错误后的准确值）
   - 人名、地名、专业术语（确保拼写和表达准确）
   - 具体的操作步骤、流程
   - 引用的原话、关键句子（纠正明显的识别错误）
   - 代码片段、命令、公式
3. **时间戳标注**：为重要内容标注对应的时间点（如果有的话）
4. **完整性优先**：宁可内容多一些，也不要遗漏重要信息
5. **结构清晰**：使用层级标题和列表组织内容

输出格式：
## 详细内容概括

### 第一部分：[主题名称]
（详细描述这部分的内容...）

### 第二部分：[主题名称]
（详细描述这部分的内容...）

### 关键信息汇总
- 重要数据：...
- 关键术语：...
- 操作步骤：...

### 原文关键句摘录
> "原句1..." —— [时间戳]
> "原句2..." —— [时间戳]

"""

    # 构造 Gemini 专用的详细内容提示词 (鼓励更长输出)
    gemini_prompt_text = f"""
请基于以下视频的音频转写和 OCR 文本(如果有），生成一份**极致详细、内容全面**的深度内容概括。

**⚠️ 我们的目标是：生成一份无需观看原视频就能获取所有细节的完整档案。不要在意长度，尽可能多地保留信息。**

**🔍 1. 深度内容解析**
- **逐字逐句的细节保留**：不仅要概括大意，更要还原讲者的具体论述逻辑、举例说明、数据支撑。
- **所有关键信息**：任何数字、年份、人名、书名、工具名、代码片段、配置参数，都必须准确记录。
- **情感与语境**：如果讲者表达了强烈观点、幽默、反讽或情绪变化，请在描述中体现。
- **不要省略**：不要使用"..."或"略过"等简写，把内容如实写出来。

**⚠️ 2. 识别错误修正与清洗**
- **智能纠错**：根据上下文主动修正 ASR/OCR 的同音字错误（如 "Python" 误识为 "派森"）。
- **屏蔽广告**：完全忽略视频中的口播广告（如“转转二手机”、“拼多多”）、求关注拉票等无关内容。
- **术语规范**：将口语化的表达转换为专业、规范的书面术语。

**📝 3. 输出结构要求**
请按照视频的时间线性流程，将内容划分为多个详细的章节。对于每个章节：
- **小标题**：清晰的主题。
- **详细段落**：使用长段落详细阐述，而不是简短的 bullet points。
- **引用原话**：对于金句或核心观点，请直接引用（修正错别字后）。
- **时间戳**：频繁标注时间戳，方便回溯。

**📊 4. 专项信息提取**
在文末请单独整理：
- **数据汇总**：所有出现的统计数据、价格、参数。
- **知识图谱**：提到的所有概念、理论、法则。
- **行动指南**：如果视频包含教程，列出一步步的操作指南。

请忽略 Token 限制，尽可能详尽地输出。

以下是输出格式参考：
## 📖 深度详细内容概括（完整版）

### [00:00 - 05:30] 章节一：背景与核心论点
（这里需要非常详细的描述，解释讲者的出发点，引用的背景故事，提出的核心矛盾...）

### [05:31 - 12:45] 章节二：深度解析技术原理
（详细解释原理的每一个步骤，不要遗漏任何技术细节...）
...

### 💡 核心知识点与数据汇总
...
"""

    # 检查是否强制使用 Gemini
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    if llm_provider == "gemini":
        print("  🔄 用户强制选择: 详细内容生成使用 Gemini API (使用增强提示词)")
        return summarize_with_gemini(full_text, custom_prompt=gemini_prompt_text)

    # 估算 token 数量
    estimated_tokens = estimate_token_count(full_text)
    
    # 如果超过 5 万 token，使用 Gemini (且没强制指定 oss)
    if estimated_tokens > 50000 and llm_provider != "oss":
        print(f"  🔄 详细内容文本过长 (>{50000:,} tokens)，使用 Gemini API (使用增强提示词)")
        # 使用Gemini处理长文本，使用详细提示词
        return summarize_with_gemini(full_text, custom_prompt=gemini_prompt_text)
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，跳过详细内容生成")
        return ("", "N/A")
    
    try:
        client = Groq(api_key=api_key)
        model_name = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
        # 详细内容使用更大的token限制
        max_tokens = int(os.getenv("GROQ_DETAIL_MAX_TOKENS", "12000"))
        temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个专业的内容整理助手，具备智能纠错能力。你的任务是：
                    - 从视频转写和OCR文本中提取所有重要信息
                    - **智能纠错**：识别并修正语音识别和OCR的同音字/词错误，特别是专业术语
                    - 生成详尽、完整的内容概括
                    - 保留原始内容中的关键细节和数据（使用修正后的准确表达）
                    - 使用清晰的结构组织信息
                    - 确保内容可以作为视频内容的完整参考
                    - 输出使用准确、专业、规范的术语表达"""
                },
                {
                    "role": "user",
                    "content": f"{default_prompt_text}\n\n以下是原始内容：\n{full_text}"
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return (response.choices[0].message.content, model_name)
    except Exception as e:
        print(f"  ⚠️  详细内容生成失败: {e}")
        return ("", "N/A")


def merge_summary_with_details(summary: str, detailed_content_tuple: tuple) -> str:
    """
    将详细内容概括追加到报告末尾。
    保持原有报告内容不变。
    """
    detailed_content, _ = detailed_content_tuple  # 解包tuple，忽略model_name
    if not detailed_content:
        return summary
    
    # 直接追加到末尾
    return summary + f"\n\n---\n\n## 📖 详细内容概括（完整版）\n\n{detailed_content}\n"


def generate_folder_name_with_llm(report_content: str, video_name: str) -> str:
    """
    使用 GPT-OSS20B 模型根据 report 内容生成简洁的文件夹名称
    
    Args:
        report_content: 完整的报告内容
        video_name: 原始视频名称（作为备用）
    
    Returns:
        生成的文件夹名称（长度限制在30个字符以内，使用下划线分隔）
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，使用默认文件夹名")
        return video_name
    
    try:
        client = Groq(api_key=api_key)
        
        # 从报告中提取关键信息（摘要部分）
        # 优先提取 "## 摘要" 部分，这是视频的核心内容概括
        summary_section = ""
        
        # 方法1: 查找 ## 摘要
        if "## 摘要" in report_content:
            parts = report_content.split("## 摘要")
            if len(parts) > 1:
                summary_part = parts[1].split("\n##")[0]
                summary_section = summary_part.strip()[:800]
        
        # 方法2: 如果没有摘要，查找 AI 智能总结后的第一段内容
        if not summary_section and "## 🤖 AI 智能总结" in report_content:
            parts = report_content.split("## 🤖 AI 智能总结")
            if len(parts) > 1:
                # 跳过空行，获取实际内容
                lines = parts[1].split('\n')
                content_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
                if content_lines:
                    summary_section = '\n'.join(content_lines[:10])[:800]
        
        # 方法3: 如果还是没有，使用报告前部分但移除格式化标记
        if not summary_section:
            import re
            # 移除所有 Markdown 标题和格式化符号
            clean_content = re.sub(r'#+\s+.*?\n', '', report_content)
            clean_content = re.sub(r'\*\*|\*|`', '', clean_content)
            summary_section = clean_content[:800].strip()
        
        prompt = f"""你的任务是为一个视频内容生成简短的文件夹名称。

这是视频的内容总结（请忽略报告格式，专注于视频讲了什么）：
{summary_section}

要求：
1. 基于视频的**核心主题和内容**生成名称，不要描述报告本身
2. 名称要**具体且有细节**，包含关键信息点（如技术栈、场景、人物等）
3. 使用下划线(_)分隔词语，不要用空格
4. 长度控制在30-40个字符（中文约15-20个字）
5. 只返回文件夹名称，不要任何解释

✅ 好的示例（要有细节）：
- Python爬虫实战_BeautifulSoup解析
- 深度学习入门_CNN图像分类
- 单反摄影技巧_人像布光教程
- Midjourney绘画_提示词技巧

❌ 避免这样（描述报告格式）：
- 视频分析报告
- 内容总结
- 知识归档

请直接返回文件夹名称："""

        # 命名任务使用轻量级模型，不占用主模型的配额
        # 优先使用 GROQ_NAMING_MODEL
        model_name = os.getenv("GROQ_NAMING_MODEL", "llama-3.1-8b-instant")
        
        print(f"  🧠 使用 LLM 生成文件夹名 (模型: {model_name})...")
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的内容标注员。你的任务是根据视频内容生成简洁、准确的主题标签，而不是描述文档格式。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3,
        )
        
        folder_name = response.choices[0].message.content.strip()

        
        # 清理文件夹名称：移除特殊字符，限制长度
        import re
        # 移除引号、换行符等
        folder_name = re.sub(r'["\'\n\r\t]', '', folder_name)
        # 移除路径分隔符
        folder_name = re.sub(r'[/\\]', '_', folder_name)
        # 移除其他不安全的文件名字符
        folder_name = re.sub(r'[<>:"|?*]', '', folder_name)
        # 限制长度
        if len(folder_name) > 50:
            folder_name = folder_name[:50]
        
        # 如果生成失败或为空，使用原始视频名
        if not folder_name or len(folder_name) < 3:
            print(f"  ⚠️  LLM 生成的文件夹名无效，使用原始名称")
            print(f"      调试信息：folder_name = '{folder_name}', 长度 = {len(folder_name) if folder_name else 0}")
            print(f"      原始响应：{response.choices[0].message.content if response else 'N/A'}")
            return video_name
        
        print(f"  ✅ LLM 生成的文件夹名: {folder_name}")
        return folder_name
        
    except Exception as e:
        print(f"  ⚠️  LLM 文件夹命名失败: {e}")
        print(f"      错误类型: {type(e).__name__}")
        import traceback
        print(f"      详细堆栈:\n{traceback.format_exc()}")
        return video_name


def generate_timeline_report(timeline: list, output_path: Path):
    """
    生成音画时间轴对照报告
    
    Args:
        timeline: 音画匹配的时间轴数据
        output_path: 输出文件路径
    """
    report = []
    report.append("# 🎬 音画时间轴对照\n")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n")
    report.append(f"**总时长**: {len(timeline)} 秒  \n")
    report.append("\n---\n")
    
    report.append("## 📊 逐秒对照表\n")
    
    for item in timeline:
        second = item['second']
        frame = item['frame']
        text = item['text']
        
        # 格式化时间
        minutes = second // 60
        seconds = second % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        report.append(f"### [{time_str}] 第 {second} 秒\n")
        report.append(f"**画面**: `{frame}`  \n")
        if text:
            report.append(f"**音频**: {text}\n")
        else:
            report.append(f"**音频**: *(无语音)*\n")
        report.append("\n")
    
    output_path.write_text('\n'.join(report), encoding='utf-8')


def generate_formatted_report(
    video_name: str,
    timestamp: str,
    transcript_text: str,
    ocr_text: str,
    summary: str,
    with_frames: bool,
    session_dir: Path,
    timeline: list = None,
    video_path: Path = None,
    model_name: str = None,
    detail_model_name: str = None,
    asr_model_name: str = None,
    video_info: dict = None
) -> str:
    """
    生成格式化的报告，包含元信息、AI总结和原始数据
    """
    # 统计信息
    transcript_chars = len(transcript_text)
    transcript_lines = transcript_text.count('\n')
    ocr_chars = len(ocr_text) if ocr_text else 0
    ocr_lines = ocr_text.count('\n') if ocr_text else 0
    
    # 格式化时间
    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    formatted_time = dt.strftime("%Y年%m月%d日 %H:%M:%S")
    
    # 使用 Markdown 格式
    report = []
    # 添加 Front Matter (如果存在元数据)
    if video_info:
        report.append("---")
        report.append(f"title: {video_info.get('title', video_name)}")
        if video_info.get('video_id'):
            report.append(f"video_id: {video_info.get('video_id')}")
        if video_info.get('platform'):
            report.append(f"platform: {video_info.get('platform')}")
        if video_info.get('upload_date'):
            report.append(f"date: {video_info.get('upload_date')}")
        if video_info.get('uploader'):
            report.append(f"uploader: {video_info.get('uploader')}")
        if video_info.get('duration'):
             report.append(f"duration: {video_info.get('duration')}")
        if video_info.get('url'):
             report.append(f"url: {video_info.get('url')}")
        report.append("tags: [Video, AI, Summary]")
        report.append("---\n")

    report.append("# 📹 视频分析报告\n")
    report.append(f"**📝 视频名称**: {video_info.get('title', video_name) if video_info else video_name}  ")
    if video_info:
        if video_info.get('platform'):
             report.append(f"**📺 平台**: {video_info.get('platform')}  ")
        if video_info.get('uploader'):
             report.append(f"**👤 作者**: {video_info.get('uploader')}  ")
        if video_info.get('url'):
            report.append(f"**🔗 原始链接**: [{video_info.get('url')}]({video_info.get('url')})  ")

    report.append(f"**🕒 处理时间**: {formatted_time}  ")
    report.append(f"**📁 输出目录**: `{session_dir.name}`  ")
    if video_path:
        report.append(f"**🎥 原始视频**: [{video_path.name}]({video_path.absolute()})  ")
    report.append(f"**🔧 处理模式**: {'完整模式 (OCR + 音频)' if with_frames else '音频模式'}  ")
    report.append("\n---\n")
    report.append("## 📊 数据统计\n")
    report.append(f"- **语音识别**: {transcript_chars} 字符, {transcript_lines} 行")
    if asr_model_name:
        report.append(f"- **ASR 模型**: {asr_model_name}")
    if with_frames:
        report.append(f"- **OCR识别**: {ocr_chars} 字符, {ocr_lines} 行")
    if model_name:
        # 显示第一次AI调用的模型
        report.append(f"- **AI 模型 (摘要)**: {model_name}")
        # 如果第二次调用使用了不同的模型，也显示
        if detail_model_name and detail_model_name != "N/A" and detail_model_name != model_name:
            report.append(f"- **AI 模型 (详细)**: {detail_model_name}")
        elif detail_model_name and detail_model_name != "N/A":
            # 如果两次使用相同模型，只显示一次但注明
            report[-1] = f"- **AI 模型**: {model_name} (摘要 + 详细)"
    report.append("\n---\n")
    
    # AI 总结（已经是 markdown 格式）
    report.append("## 🤖 AI 智能总结\n")
    report.append(summary)
    report.append("\n---\n")
    
    # 原始数据引用
    report.append("## 📂 原始数据文件\n")
    report.append(f"- 📄 [语音识别原文](transcript_raw.md) ({transcript_chars} 字符)")
    if with_frames:
        report.append(f"- 📄 [OCR识别原文](ocr_raw.md) ({ocr_chars} 字符)")
        report.append(f"- 📁 视频帧图片: `frames/` 目录")
        if timeline:
            report.append(f"- 🎬 [音画时间轴对照](timeline.md) (逐秒匹配)")
    report.append(f"- 🔊 音频文件: `{video_name}.wav`")
    report.append("\n> 💡 **提示**: 点击链接查看原始数据文件获取完整的识别内容\n")
    report.append("---\n")
    report.append(f"*📌 报告生成时间: {formatted_time}*")
    
    return "\n".join(report)


def extract_summary_from_report(summary: str) -> str:
    """从AI报告中提取摘要（不超过50字）"""
    # 查找摘要部分
    summary_patterns = [
        r'##\s*摘要\s*\n+(.+?)(?:\n\n|\n##)',  # ## 摘要 后的内容
        r'摘要[：:]\s*(.+?)(?:\n\n|\n##)',     # 摘要: 后的内容
    ]
    
    for pattern in summary_patterns:
        matches = re.findall(pattern, summary, re.DOTALL | re.MULTILINE)
        if matches:
            extracted = matches[0].strip()
            # 移除Markdown格式
            extracted = re.sub(r'\*\*|\*|`|#|\[|\]|\(.*?\)', '', extracted)
            # 限制长度为50字
            if len(extracted) > 50:
                extracted = extracted[:50]
            return extracted
    
    # 如果没找到摘要章节，尝试提取第一段非标题内容
    lines = summary.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('*') and len(line) > 10:
            # 移除Markdown格式
            line = re.sub(r'\*\*|\*|`|#|\[|\]|\(.*?\)', '', line)
            if len(line) > 50:
                return line[:50]
            return line
    
    return "暂无摘要"


def extract_tags_from_summary(summary: str) -> list:
    """从AI总结中提取标签"""
    tags = []
    
    # 查找标签行（支持多种格式）
    tag_patterns = [
        r'##\s*标签\s*\n+(.+?)(?:\n\n|\n##)',  # ## 标签 后的内容
        r'标签[：:]\s*(.+)',
        r'Tags[：:]\s*(.+)',
        r'关键词[：:]\s*(.+)',
        r'Keywords[：:]\s*(.+)',
    ]
    
    for pattern in tag_patterns:
        matches = re.findall(pattern, summary, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            # 移除Markdown格式（粗体、斜体等）
            clean_match = re.sub(r'\*\*|\*|`|#', '', match)
            # 移除引号
            clean_match = re.sub(r'["""\'\'"]', '', clean_match)
            # 移除换行
            clean_match = clean_match.replace('\n', ' ')
            # 分割标签（支持逗号、顿号、空格、分号等分隔符）
            tag_list = re.split(r'[,，、\s;；]+', clean_match.strip())
            tags.extend([t.strip() for t in tag_list if t.strip()])
    
    # 去重并过滤
    seen = set()
    unique_tags = []
    for tag in tags:
        # 清理每个标签
        tag = re.sub(r'[^\w\u4e00-\u9fa5\-]', '', tag)  # 只保留字母、数字、中文、连字符
        tag_lower = tag.lower()
        if tag_lower not in seen and len(tag) > 1 and len(tag) < 20:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return unique_tags[:10]  # 最多返回10个标签


def extract_topics_from_summary(summary: str, video_duration: float = 0) -> list:
    """从AI总结中提取主题章节"""
    topics = []
    
    # 查找章节标题（## 开头）
    lines = summary.split('\n')
    current_topic = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 检测章节标题
        if line.startswith('##') and not line.startswith('###'):
            title = line.lstrip('#').strip()
            
            # 过滤掉一些非章节的标题
            skip_titles = ['AI 智能总结', '数据统计', '原始数据', '总结', '标签', 'Tags', '关键词']
            if any(skip in title for skip in skip_titles):
                continue
            
            # 提取时间范围（如果有）
            time_match = re.search(r'\[?(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\]?', line)
            
            if time_match:
                start_min, start_sec, end_min, end_sec = map(int, time_match.groups())
                start_time = start_min * 60 + start_sec
                end_time = end_min * 60 + end_sec
            else:
                # 如果没有明确时间，按顺序分配
                start_time = (len(topics) * video_duration / 5) if video_duration > 0 else 0
                end_time = min(start_time + video_duration / 5, video_duration) if video_duration > 0 else 0
            
            # 收集描述（下面几行非标题内容）
            description_lines = []
            for j in range(i + 1, min(i + 5, len(lines))):
                desc_line = lines[j].strip()
                if desc_line and not desc_line.startswith('#'):
                    description_lines.append(desc_line)
                elif desc_line.startswith('##'):
                    break
            
            description = ' '.join(description_lines)[:200]
            
            topics.append({
                'title': title[:100],
                'start_time': start_time,
                'end_time': end_time,
                'description': description,
                'keywords': []  # 可以后续从描述中提取
            })
    
    return topics[:20]  # 最多返回20个主题


def save_to_database(
    video_path: Path,
    video_name: str,
    session_dir: Path,
    transcript_text: str,
    ocr_text: str,
    summary: str,
    transcript_data: dict,
    timeline: list = None,
    with_frames: bool = False,
    video_duration: float = 0,
    source_url: str = None,
    platform_title: str = None,
    ocr_engine: str = None,
) -> int:
    """
    将处理结果保存到数据库
    
    Returns:
        int: 视频ID
    """
    try:
        repo = VideoRepository()
        
        # 1. 创建视频记录
        print("\n💾 保存到数据库...")
        
        # 计算文件哈希
        content_hash = repo.calculate_content_hash(str(video_path))
        
        # 检查是否已存在
        existing = repo.get_video_by_hash(content_hash)
        if existing:
            print(f"   ⚠️  视频已存在 (ID: {existing.id})，更新产物...")
            video_id = existing.id
            # 更新视频元数据（时长、标题等）
            repo.update_video_metadata(
                video_id=video_id,
                duration_seconds=video_duration,
                title=platform_title or video_name,
                platform_title=platform_title
            )
        else:
            # 判断来源类型
            if source_url:
                if 'bilibili.com' in source_url:
                    source_type = SourceType.BILIBILI
                elif 'youtube.com' in source_url or 'youtu.be' in source_url:
                    source_type = SourceType.YOUTUBE
                else:
                    source_type = SourceType.URL
            else:
                source_type = SourceType.LOCAL
            
            video = Video(
                content_hash=content_hash,
                video_id=None,
                source_type=source_type,
                source_url=source_url,
                platform_title=platform_title or video_name,
                title=platform_title or video_name,
                duration_seconds=video_duration,
                file_path=str(video_path),
                file_size_bytes=video_path.stat().st_size,
                processing_config={
                    'with_frames': with_frames,
                    'output_dir': str(session_dir)
                },
                status=ProcessingStatus.COMPLETED
            )
            
            video_id = repo.create_video(video)
            print(f"   ✅ 创建视频记录 (ID: {video_id})")
        
        # 2. 保存产物
        # 2.1 语音转写
        if transcript_text.strip():
            transcript_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.TRANSCRIPT,
                content_text=transcript_text,
                content_json=transcript_data,
                file_path=str(session_dir / "transcript_raw.md"),
                model_name="groq-whisper-large-v3",
                char_count=len(transcript_text)
            )
            repo.save_artifact(transcript_artifact)
            print(f"   ✅ 保存语音转写 ({len(transcript_text)} 字符)")
        
        # 2.2 OCR识别
        if with_frames and ocr_text.strip():
            model_name = "apple-vision-ocr" if (ocr_engine or OCR_ENGINE) == 'vision' else "paddleocr-v4"
            ocr_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.OCR,
                content_text=ocr_text,
                file_path=str(session_dir / "ocr_raw.md"),
                model_name=model_name,
                char_count=len(ocr_text)
            )
            repo.save_artifact(ocr_artifact)
            print(f"   ✅ 保存OCR识别 ({len(ocr_text)} 字符)")
        
        # 2.3 AI报告
        if summary.strip():
            report_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.REPORT,
                content_text=summary,
                file_path=str(session_dir / "report.md"),
                model_name="groq-llama3-120b",
                char_count=len(summary)
            )
            repo.save_artifact(report_artifact)
            print(f"   ✅ 保存AI报告 ({len(summary)} 字符)")
        
        # 3. 提取并保存标签
        tags = extract_tags_from_summary(summary)
        if tags:
            repo.save_tags(video_id, tags, source='auto', confidence=0.8)
            print(f"   ✅ 保存标签: {', '.join(tags)}")
        
        # 4. 提取并保存主题
        topics = extract_topics_from_summary(summary, video_duration)
        if topics:
            topic_objects = []
            for t in topics:
                topic = Topic(
                    video_id=video_id,
                    title=t['title'],
                    start_time=t['start_time'],
                    end_time=t['end_time'],
                    summary=t['description'],
                    keywords=t['keywords']
                )
                topic_objects.append(topic)
            
            repo.save_topics(video_id, topic_objects)
            print(f"   ✅ 保存主题: {len(topics)} 个章节")
        
        # 5. 保存时间线
        if timeline and len(timeline) > 0:
            timeline_entries = []
            for entry in timeline[:100]:  # 限制数量
                if entry.get('text'):
                    tl = TimelineEntry(
                        video_id=video_id,
                        timestamp_seconds=entry['second'],
                        transcript_text=entry['text'][:500]
                    )
                    timeline_entries.append(tl)
            
            if timeline_entries:
                repo.save_timeline(video_id, timeline_entries)
                print(f"   ✅ 保存时间线: {len(timeline_entries)} 个条目")
        
        # 6. 更新全文搜索索引
        print("   🔍 更新全文搜索索引...")
        repo.update_fts_index(video_id)
        
        print(f"   ✅ 数据库保存完成！(视频ID: {video_id})")
        print(f"   💡 可以使用 `make db-show ID={video_id}` 查看详情")
        print(f"   💡 可以使用 `make search Q=\"关键词\"` 来搜索")
        
        return video_id
        
    except Exception as e:
        print(f"   ❌ 数据库保存失败: {e}")
        import traceback
        traceback.print_exc()
        return None


# ========== 主控制流程 ==========
def process_video(
    video_path: Path,
    output_dir: Path,
    with_frames: bool = False,
    ocr_lang: str = "ch",
    ocr_det_model: str = "mobile",
    ocr_rec_model: str = "mobile",
    use_gpu: bool = False,
    source_url: str = None,
    platform_title: str = None,
    ocr_engine: str = None,  # 新增：'vision' 或 'paddle'，None=自动选择
    smart_ocr: bool = True,  # 新增：是否启用智能抽帧
    cover_image_path: Path = None, # 新增：封面图片路径
    video_info: dict = None, # 新增：视频元数据
):
    ensure_dir(output_dir)

    # 1. 创建输出文件夹
    # 逻辑：优先复用 output/<video_name> 目录（方便与 download 阶段生成的 README.md 合并）
    # 只有当该目录已存在且包含 report.md（说明是之前的完整运行）时，才创建带时间戳的新目录
    video_name = video_path.stem
    default_session_dir = output_dir / video_name
    
    if default_session_dir.exists() and (default_session_dir / "report.md").exists():
        # 旧记录存在，创建新目录保留历史
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = output_dir / f"{video_name}_{timestamp}"
        print(f"⚠️  目录 {default_session_dir} 已存在且包含报告，将创建新目录: {session_dir}")
    else:
        # 复用目录（download 阶段可能已创建并放入了 README.md）
        session_dir = default_session_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    ensure_dir(session_dir)
    
    # 2. 各类文件路径
    audio_path = session_dir / f"{video_name}.wav"
    frames_dir = session_dir / "frames"
    ocr_raw_path = session_dir / "ocr_raw.md"
    transcript_raw_path = session_dir / "transcript_raw.md"
    report_path = session_dir / "report.md"
    
    print(f"\n📁 输出目录: file://{session_dir}")
    print(f"   时间戳: {timestamp}\n")

    # 获取视频时长
    print(">> 获取视频时长...")
    video_duration = get_video_duration(video_path)
    print(f"   ⏱️  视频时长: {video_duration:.2f} 秒 ({int(video_duration // 60)}:{int(video_duration % 60):02d})")

    ocr_text = ""
    transcript_text = ""
    current_fps = 1
    
    # 1.5 尝试识别封面/截图内容 (无论是否开启 frames OCR)
    screenshot_ocr_text = ""
    if cover_image_path and cover_image_path.exists():
        # 保存截图/封面图片到 session 目录
        try:
            import shutil
            dest_cover_path = session_dir / f"screenshot{cover_image_path.suffix}"
            shutil.copy(cover_image_path, dest_cover_path)
            print(f"   🖼️  网页截图/封面图片已保存: {dest_cover_path.name}")
        except Exception as e:
            print(f"   ⚠️  保存网页截图/封面图片失败: {e}")

        print(f"\n🖼️  正在识别网页截图/封面文字: {cover_image_path.name} ...")
        try:
            import shutil
            
            # 使用 session 目录下的 cover_frames 文件夹处理封面图片，不再使用系统临时目录
            temp_dir_path = session_dir / "cover_frames"
            temp_dir_path.mkdir(parents=True, exist_ok=True)
            
            # 如果有 split_long_image，使用分割
            if split_long_image:
                try:
                    chunks = split_long_image(cover_image_path, output_dir=temp_dir_path)
                    if chunks:
                        for idx, chunk_path in enumerate(chunks):
                            # 强制使用 .png, 兼容 ocr_vision 中硬编码的 "frame_*.png"
                            target_path = temp_dir_path / f"frame_{idx+1:04d}.png"
                            if chunk_path != target_path:
                                if chunk_path.exists() and chunk_path.parent == temp_dir_path:
                                    # 如果因为扩展名不同，需要转换格式
                                    if chunk_path.suffix.lower() != ".png":
                                        from PIL import Image
                                        with Image.open(chunk_path) as img:
                                            img.save(target_path)
                                        chunk_path.unlink()
                                    else:
                                        chunk_path.rename(target_path)
                                else:
                                    # Original file returned, copy or convert it
                                    if chunk_path.suffix.lower() != ".png":
                                        from PIL import Image
                                        with Image.open(chunk_path) as img:
                                            img.save(target_path)
                                    else:
                                        shutil.copy(chunk_path, target_path)
                        
                        if len(chunks) > 1:
                            print(f"   ℹ️  封面已分割为 {len(chunks)} 个片段")
                except Exception as e:
                    print(f"   ⚠️  封面分割/处理失败: {e}")
                    # 回退到单图复制
                    temp_cover_file = temp_dir_path / "frame_0001.png"
                    if cover_image_path.suffix.lower() != ".png":
                        from PIL import Image
                        with Image.open(cover_image_path) as img:
                            img.save(temp_cover_file)
                    else:
                        shutil.copy(cover_image_path, temp_cover_file)
            else:
                # 回退到单图复制
                temp_cover_file = temp_dir_path / "frame_0001.png"
                if cover_image_path.suffix.lower() != ".png":
                    from PIL import Image
                    with Image.open(cover_image_path) as img:
                        img.save(temp_cover_file)
                else:
                    shutil.copy(cover_image_path, temp_cover_file)
            
            selected_engine = ocr_engine or OCR_ENGINE
            temp_ocr_text = ""
            
            if selected_engine == 'vision':
                # Vision OCR (macOS)
                if init_vision_ocr:
                    ocr_instance = init_vision_ocr(lang=ocr_lang)
                    # Vision OCR helper 需要 output_path 参数
                    temp_ocr_text = ocr_folder_vision(ocr_instance, temp_dir_path, output_path=None, debug=False)
                else:
                    print("   ⚠️  Vision OCR 模块未加载")
                    
            elif selected_engine == 'paddle':
                # PaddleOCR
                if init_ocr:
                    ocr_instance = init_ocr(
                        lang=ocr_lang, use_gpu=use_gpu, 
                        det_model=ocr_det_model, rec_model=ocr_rec_model
                    )
                    temp_ocr_text = ocr_folder_to_text(
                        ocr_instance, str(temp_dir_path),
                        min_score=0.3, debug=False, use_preprocessing=True
                    )
                else:
                    print("   ⚠️  PaddleOCR 模块未加载")
            
            if temp_ocr_text.strip():
                screenshot_ocr_text = temp_ocr_text
                print(f"   ✅ 网页截图/封面识别成功: {len(screenshot_ocr_text)} 字符")
                
                # 保存封面 OCR 结果
                screenshot_ocr_path = session_dir / "screenshot_ocr.md"
                with open(screenshot_ocr_path, "w", encoding="utf-8") as f:
                    f.write(f"# 网页截图/封面 OCR 结果\n\n{screenshot_ocr_text}")
            else:
                print("   ℹ️  网页截图/封面未识别到文字")
                
        except Exception as e:
            print(f"   ⚠️  网页截图/封面 OCR 过程出错: {e}")

    # 2. 如果是OCR模式，先处理视频帧和OCR
    if with_frames:
        print("\n" + "="*60)
        print("📹 第一步：处理视频帧 OCR")
        print("="*60)
        
        if smart_ocr and SMART_EXTRACT_AVAILABLE:
            print(">> 🚀 智能抽帧处理中（变化触发 & 稳定等待 & 双阈值）...")
            try:
                # 使用双阈值迟滞 + 稳定等待 + 图像融合
                extractor = SmartFrameExtractor(
                    fps=5.0,                  # 采样率 5 FPS (每秒5帧)
                    diff_threshold=2.0,       # T_enter: 降低变化阈值 (更敏感，2.0)
                    static_threshold=3.0,     # T_exit:  放宽稳定阈值 (更容易判定稳定，3.0)
                    static_duration_frames=2, # M: 连续 2 帧稳定即可捕获
                    enable_fusion=True        # 启用多帧融合增强
                )
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir_str:
                    extractor.extract(
                        video_path=video_path, 
                        output_dir=frames_dir, 
                        temp_dir=Path(temp_dir_str)
                    )
                current_fps = extractor.fps
            except Exception as e:
                print(f"❌ 智能抽帧失败，回退到普通抽帧: {e}")
                import traceback
                traceback.print_exc()
                extract_frames(video_path, frames_dir, fps=1)
                current_fps = 1
        else:
            print(">> 抽帧中（固定 1 FPS）...")
            extract_frames(video_path, frames_dir, fps=1)
            current_fps = 1

        print("\n>> OCR 处理中...")
        
        # 决定使用哪个 OCR 引擎
        selected_engine = ocr_engine or OCR_ENGINE
        
        if selected_engine == 'vision':
            if init_vision_ocr:
                print(f"   🍎 使用 Apple Vision OCR (lang={ocr_lang})")
                try:
                    ocr = init_vision_ocr(
                        lang=ocr_lang,
                        recognition_level='accurate',  # 'fast' 或 'accurate'
                    )
                    ocr_text = ocr_folder_vision(
                        ocr,
                        frames_dir,
                        output_path=ocr_raw_path,
                        debug=False,
                    )
                except Exception as e:
                    print(f"   ⚠️  Vision OCR 失败，尝试降级到 PaddleOCR: {e}")
                    selected_engine = 'paddle'
            else:
                print(f"   ⚠️  Vision OCR 未加载，尝试降级到 PaddleOCR")
                selected_engine = 'paddle'
        
        if selected_engine == 'paddle':
            # 使用多进程并行处理以提升CPU利用率
            if PARALLEL_OCR_AVAILABLE:
                import os
                # 从环境变量读取工作进程数，如果未设置则使用CPU核心数/2
                ocr_workers_env = os.environ.get('OCR_WORKERS', '').strip()
                if ocr_workers_env and ocr_workers_env.lower() != 'auto':
                    try:
                        num_workers = max(1, int(ocr_workers_env))
                    except ValueError:
                        num_workers = max(1, os.cpu_count() // 2)
                else:
                    num_workers = max(1, os.cpu_count() // 2)
                
                print(f"   🐼 使用 PaddleOCR (多进程, workers={num_workers})")
                ocr_text = ocr_folder_parallel(
                    str(frames_dir),
                    min_score=0.3,
                    num_workers=num_workers,
                    use_preprocessing=True,
                    hybrid_mode=True,
                )
            else:
                # 降级到单进程模式
                if init_ocr:
                    print(f"   🐼 使用 PaddleOCR (det={ocr_det_model}, rec={ocr_rec_model})")
                    ocr = init_ocr(
                        lang=ocr_lang,
                        use_gpu=use_gpu,
                        det_model=ocr_det_model,
                        rec_model=ocr_rec_model
                    )
                    ocr_text = ocr_folder_to_text(
                        ocr, 
                        str(frames_dir), 
                        min_score=0.3,
                        debug=False,
                        use_preprocessing=True,
                        roi_bottom_only=True,
                        hybrid_mode=True,
                    )
                else:
                    print("   ❌ OCR 引擎不可用 (PaddleOCR 未加载)")
                    ocr_text = ""
        
        if ocr_text.strip():
            char_count = len(ocr_text)
            line_count = ocr_text.count('\n')
            print(f"\n✅ OCR 完成！识别 {char_count} 字符，{line_count} 行")
            
            # 保存OCR原始结果（Markdown 格式）
            print(f"   💾 保存OCR原始结果: {ocr_raw_path.name}")
            ocr_markdown = f"# 🔍 OCR 识别原始数据\n\n"
            ocr_markdown += f"**识别时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n"
            ocr_markdown += f"**总字符数**: {char_count}  \n"
            ocr_markdown += f"**总行数**: {line_count}  \n"
            ocr_markdown += f"**处理模式**: 混合模式（字幕区 + 全画面）\n\n"
            ocr_markdown += "---\n\n"
            ocr_markdown += "## 📝 识别内容\n\n"
            ocr_markdown += "```\n"
            ocr_markdown += ocr_text
            ocr_markdown += "\n```\n"
            ocr_raw_path.write_text(ocr_markdown, encoding="utf-8")
        else:
            print("⚠️  警告：OCR 未识别到任何文字（可能视频中没有文字内容）")
        
        print("\n" + "="*60)
        print("🎤 第二步：处理音频转写")
        print("="*60)
    
    # 3. 处理音频（OCR模式在OCR之后，普通模式直接处理）
    print(">> 提取音频中...")
    extract_audio(video_path, audio_path)

    # 4. Groq 语音转文字（带时间戳）
    print(">> 调用 Groq 语音转写（带时间戳）...")
    transcript_data = transcribe_audio_with_groq(audio_path)
    transcript_text = transcript_data.get('text', '')
    asr_model_name = transcript_data.get('asr_model', 'Groq Whisper')
    
    # 保存语音识别原始结果（Markdown 格式，包含时间戳）
    if transcript_text.strip():
        print(f"   💾 保存语音识别原始结果: {transcript_raw_path.name}")
        transcript_markdown = f"# 🎤 语音识别原始数据\n\n"
        transcript_markdown += f"**识别时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n"
        transcript_markdown += f"**总字符数**: {len(transcript_text)}  \n"
        transcript_markdown += f"**识别模型**: {asr_model_name}  \n"
        transcript_markdown += f"**片段数量**: {len(transcript_data.get('segments', []))}  \n\n"
        transcript_markdown += "---\n\n"
        transcript_markdown += "## 📝 完整转写\n\n"
        transcript_markdown += transcript_text + "\n\n"
        
        # 添加带时间戳的片段
        if transcript_data.get('segments'):
            transcript_markdown += "---\n\n"
            transcript_markdown += "## ⏱️ 时间戳片段\n\n"
            for seg in transcript_data['segments']:
                start_time = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
                end_time = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
                transcript_markdown += f"**[{start_time} - {end_time}]** {seg['text']}\n\n"
        
        transcript_raw_path.write_text(transcript_markdown, encoding="utf-8")

    # 4.5 生成音画匹配时间轴
    timeline = None
    if with_frames and transcript_data.get('segments'):
        print(">> 生成音画时间轴匹配...")
        timeline = match_audio_with_frames(transcript_data, frames_dir, fps=current_fps, duration=video_duration)
        timeline_path = session_dir / "timeline.md"
        generate_timeline_report(timeline, timeline_path)
        print(f"   💾 保存音画时间轴: {timeline_path.name}")

    # 5. 合并文本：构建带时间戳的转写文本（用于所有 AI 任务）
    # 用户要求：启动第一轮和第二轮总结的时候，只输入时间戳片段，不额外重复包含完整转写
    combined_text_parts = ["=== Audio Transcript with Timestamps ===\n"]
    if transcript_data.get('segments'):
        for seg in transcript_data['segments']:
            start_time = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            end_time = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
            combined_text_parts.append(f"[{start_time} - {end_time}] {seg['text']}")
    else:
        # 如果没有 segments（例如纯音频且未拆分），则使用纯文本
        combined_text_parts.append(transcript_text)

    if with_frames and ocr_text:
        combined_text_parts.append(f"\n\n=== OCR from Frames ===\n{ocr_text}\n")

    if screenshot_ocr_text:
        combined_text_parts.append(f"\n\n=== OCR from Webpage Screenshot/Cover ===\n{screenshot_ocr_text}\n")

    combined_text = "\n".join(combined_text_parts)

    # 6. 第一次AI调用：生成结构化摘要报告
    print("\n>> 第一次AI调用：生成结构化摘要...")
    # 使用带时间戳的文本进行摘要（符合用户要求：只输入时间戳片段）
    summary, model_name = summarize_with_gpt_oss_120b(combined_text)
    
    # 7. 第二次AI调用：生成详细内容概括
    print(">> 第二次AI调用：生成详细内容概括...")
    # 使用同一份文本
    detailed_content_tuple = generate_detailed_content(combined_text)
    detailed_content, detail_model_name = detailed_content_tuple  # 解包 tuple，保存第二次调用的 model_name

    
    # 8. 合并摘要和详细内容
    if detailed_content:
        print(">> 合并摘要与详细内容...")
        summary = merge_summary_with_details(summary, detailed_content_tuple)
        print(f"   ✅ 详细内容已添加 ({len(detailed_content)} 字符)")

    # 9. 生成格式化报告
    report_content = generate_formatted_report(
        video_name=video_name,
        timestamp=timestamp,
        transcript_text=transcript_text,
        ocr_text=ocr_text,
        summary=summary,
        with_frames=with_frames,
        session_dir=session_dir,
        timeline=timeline,
        video_path=video_path,
        model_name=model_name,
        detail_model_name=detail_model_name,
        asr_model_name=asr_model_name,
        video_info=video_info
    )
    
    report_path.write_text(report_content, encoding="utf-8")
    # 使用引号包裹路径或拼接 file:// 协议，以便终端在遇到路径中的逗号等特殊字符时仍能正确生成可点击链接
    print(f"\n📄 报告已保存到: file://{report_path}")
    print(f"📁 完整输出目录: file://{session_dir}")
    
    # 9.5 使用 LLM 生成语义化的文件夹名称并重命名
    print("\n>> 使用 LLM 生成语义化文件夹名...")
    new_folder_name = generate_folder_name_with_llm(report_content, video_name)
    
    # 如果生成的名称与原始名称不同，则重命名文件夹
    if new_folder_name != video_name:
        new_session_dir = output_dir / f"{new_folder_name}_{timestamp}"
        try:
            session_dir.rename(new_session_dir)
            session_dir = new_session_dir  # 更新引用
            print(f"   ✅ 文件夹已重命名为: {session_dir.name}")
            print(f"   🔗 新输出目录: file://{session_dir}")
            
            # 更新路径引用
            report_path = session_dir / "report.md"
            
        except Exception as e:
            print(f"   ⚠️  文件夹重命名失败: {e}")
            print(f"   保持原文件夹名: {session_dir.name}")
    
    # 10. 保存到数据库
    save_to_database(
        video_path=video_path,
        video_name=video_name,
        session_dir=session_dir,
        transcript_text=transcript_text,
        ocr_text=ocr_text,
        summary=summary,
        transcript_data=transcript_data,
        timeline=timeline,
        with_frames=with_frames,
        video_duration=video_duration,
        source_url=source_url,
        platform_title=platform_title,
        ocr_engine=ocr_engine,
    )



# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="Video → Text Report pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  # 处理本地视频文件
  python process_video.py video.mp4
  python process_video.py video.mp4 --with-frames
  
  # 从URL下载并处理（如果安装了 video_downloader）
  python process_video.py "https://www.youtube.com/watch?v=xxxxx"
  python process_video.py "https://www.bilibili.com/video/BVxxxxx" --with-frames
        """
    )
    parser.add_argument("video", type=str, help="输入视频路径或URL")
    parser.add_argument(
        "--with-frames",
        action="store_true",
        help="是否启用抽帧 + OCR 分支",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output",
        help="输出目录（默认: ./output）",
    )
    parser.add_argument(
        "--ocr-lang",
        type=str,
        default="ch",
        help="OCR 语言（默认: ch）",
    )
    parser.add_argument(
        "--ocr-engine",
        type=str,
        default=None,
        choices=["vision", "paddle"],
        help="OCR 引擎选择（默认: 自动选择）",
    )
    parser.add_argument(
        "--ocr-det-model",
        type=str,
        default="server",  # 改为 server 以获得更好的效果
        choices=["server", "mobile"],
        help="PaddleOCR 检测模型类型（默认: server，复杂背景建议使用）",
    )
    parser.add_argument(
        "--ocr-rec-model",
        type=str,
        default="server",  # 改为 server 以获得更好的效果
        choices=["server", "mobile"],
        help="OCR 识别模型类型（默认: server，提升准确度）",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        help="是否使用 GPU 加速",
    )
    parser.add_argument(
        "--legacy-ocr",
        action="store_true",
        help="是否使用传统固定 1 FPS 抽帧（禁用智能抽帧）",
    )
    parser.add_argument(
        "--download-dir",
        type=str,
        default="videos",
        help="视频下载目录（默认: videos/）",
    )
    
    args = parser.parse_args()

    # 检测输入是URL还是文件路径
    input_str = args.video
    is_url = input_str.startswith("http://") or input_str.startswith("https://")
    
    source_url = None
    platform_title = None
    
    cover_image_path = None
    video_info = {}
    
    if is_url:
        # 如果是URL，尝试下载
        if not DOWNLOADER_AVAILABLE:
            print("❌ 错误：检测到URL但未安装 video_downloader 模块")
            print("   请先安装依赖: pip install yt-dlp")
            exit(1)
        
        print(f"📥 检测到URL，开始下载...")
        downloader = VideoDownloader(download_dir=args.download_dir)
        
        try:
            file_info = downloader.download_video(input_str)
            video_path = file_info.file_path
            source_url = input_str
            platform_title = getattr(file_info, 'title', None)
            cover_image_path = getattr(file_info, 'screenshot_path', None)
            
            # 提取元数据
            video_info = {
                'title': getattr(file_info, 'title', None),
                'video_id': getattr(file_info, 'video_id', None),
                'platform': getattr(file_info, 'platform', None),
                'duration': getattr(file_info, 'duration', None),
                'uploader': getattr(file_info, 'uploader', None),
                'upload_date': getattr(file_info, 'upload_date', None),
                'url': input_str
            }
            
            print(f"✅ 下载完成: {video_path}")
            if cover_image_path:
                 print(f"🖼️  下载封面: {cover_image_path}")
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            exit(1)
    else:
        # 如果是本地文件路径
        video_path = Path(input_str).resolve()
        if not video_path.exists():
            print(f"❌ 错误：视频文件不存在: {video_path}")
            exit(1)
            
        # 尝试查找同名封面/截图图片
        # 优先查找 _screenshot 后缀（网页截图），其次查找同名图片（封面/缩略图）
        potential_covers = [
            # 网页截图（包含更多信息）优先
            video_path.parent / f"{video_path.stem}_screenshot.png",
            video_path.parent / f"{video_path.stem}_screenshot.jpg",
            # 其次是缩略图/封面
            video_path.with_suffix(".jpg"),
            video_path.with_suffix(".png"),
            video_path.with_suffix(".webp"),
        ]
        for p in potential_covers:
            if p.exists():
                cover_image_path = p
                print(f"🖼️  发现本地截图/封面: {cover_image_path.name}")
                break

    output_dir = Path(args.out_dir).resolve()

    process_video(
        video_path=video_path,
        output_dir=output_dir,
        with_frames=args.with_frames,
        ocr_lang=args.ocr_lang,
        ocr_engine=args.ocr_engine,
        ocr_det_model=args.ocr_det_model,
        ocr_rec_model=args.ocr_rec_model,
        use_gpu=args.use_gpu,
        source_url=source_url,
        platform_title=platform_title,
        smart_ocr=not args.legacy_ocr,
        cover_image_path=cover_image_path,
        video_info=video_info
    )


def process_video_cli(args):
    """统一CLI适配函数"""
    # 将统一CLI的参数映射到 process_video 函数
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"❌ 错误：视频文件不存在: {video_path}")
        exit(1)
    
    output_dir = Path("output").resolve()
    
    # 参数映射
    with_frames = args.ocr
    ocr_engine = args.ocr_engine if hasattr(args, 'ocr_engine') else 'vision'
    use_gpu = args.use_gpu if hasattr(args, 'use_gpu') else False
    skip_audio = args.skip_audio if hasattr(args, 'skip_audio') else False
    skip_llm = args.skip_llm if hasattr(args, 'skip_llm') else False
    smart_ocr = not args.legacy_ocr if hasattr(args, 'legacy_ocr') else True
    
    process_video(
        video_path=video_path,
        output_dir=output_dir,
        with_frames=with_frames,
        ocr_lang="ch",
        ocr_engine=ocr_engine,
        ocr_det_model="server",
        ocr_rec_model="server",
        use_gpu=use_gpu,
        source_url=None,
        platform_title=None,
        smart_ocr=smart_ocr,
    )


if __name__ == "__main__":
    main()
