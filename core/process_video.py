# process_video.py
import argparse
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
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

from ocr.ocr_utils import init_ocr, ocr_folder_to_text

# 导入多进程OCR（用于提升CPU利用率）
try:
    from ocr.ocr_parallel import ocr_folder_parallel
    PARALLEL_OCR_AVAILABLE = True
except ImportError:
    PARALLEL_OCR_AVAILABLE = False
    print("⚠️  多进程OCR模块不可用，将使用单进程模式")

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


def match_audio_with_frames(transcript_data: dict, frames_dir: Path, fps: int = 1) -> list:
    """
    音画匹配：将音频转写片段与视频帧关联。
    
    Args:
        transcript_data: 包含 segments 的转写数据
        frames_dir: 视频帧目录
        fps: 抽帧频率（每秒帧数）
    
    Returns:
        list: [{'second': 0, 'frame': 'frame_00001.png', 'text': '对应的文本'}, ...]
    """
    import glob
    
    # 获取所有帧文件
    frame_files = sorted(glob.glob(str(frames_dir / "frame_*.png")))
    frame_count = len(frame_files)
    
    # 为每一秒建立文本索引
    timeline = []
    
    for i in range(frame_count):
        second = i  # 帧编号从1开始，对应第 i 秒
        frame_name = f"frame_{i+1:05d}.png"
        
        # 查找这一秒对应的文本
        texts_in_second = []
        if 'segments' in transcript_data:
            for seg in transcript_data['segments']:
                seg_start = int(seg['start'])
                seg_end = int(seg['end'])
                # 如果片段覆盖当前秒
                if seg_start <= second < seg_end:
                    texts_in_second.append(seg['text'].strip())
        
        timeline.append({
            'second': second,
            'frame': frame_name,
            'text': ' '.join(texts_in_second) if texts_in_second else ''
        })
    
    return timeline


# ========== Groq API 集成 ==========
def _transcribe_single_audio(client, model: str, audio_path: Path) -> dict:
    """
    转写单个音频文件（内部函数）。
    """
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(audio_path.name, audio_file.read()),
            model=model,
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
        model = os.getenv("GROQ_ASR_MODEL", "whisper-large-v3-turbo")
        
        # 检查文件大小，决定是否需要拆分
        file_size = audio_path.stat().st_size
        
        if file_size <= MAX_AUDIO_SIZE_BYTES:
            # 文件足够小，直接转写
            return _transcribe_single_audio(client, model, audio_path)
        
        # 文件过大，需要拆分
        chunks = split_audio(audio_path)
        
        if len(chunks) == 1:
            # 拆分失败或不需要拆分，尝试直接上传
            return _transcribe_single_audio(client, model, audio_path)
        
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
            'segments': all_segments
        }
        
    except Exception as e:
        print(f"  ✗ Groq 转写失败: {e}")
        return {
            'text': f"[转写失败: {str(e)}]",
            'segments': []
        }


def summarize_with_gpt_oss_120b(full_text: str) -> str:
    """
    使用 Groq 的 LLM 进行文本总结。
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，返回原文")
        return f"[FAKE SUMMARY - 请在 .env 中设置 GROQ_API_KEY]\n\n{full_text}"
    
    try:
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
        # 增加 token 限制以支持更长的输出
        max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "8192"))  # 从 4096 提升到 8192
        temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
        
        prompt = f"""

请将以下“带时间戳的音频转写 + OCR 文本”整理成一份**结构化 Markdown 知识档案和内容概要**。

你需要：
1. **使用 Markdown** 输出（标题、列表、引用、表格等）
2. 按时间顺序梳理主要片段，并为关键内容标注对应时间戳
3. 合并音频与 OCR 内容：  
   - 如果 OCR 文字不完整，请根据上下文**推断合理含义**  
   - 如果某些屏幕文字重要（如 PPT、界面按钮、参数、代码），请单独提取并解释
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
## OCR 信息与推断（列出重要屏幕文字并解释）
## 时间线（关键片段 + 时间戳）
## 关键句（含时间戳）
## 标签
格式：标签: 标签1, 标签2, 标签3

以下是内容：
{full_text[:40000]}  



"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个多模态知识档案生成器。

                    输入来自同一段视频，包括：
                    - 带时间戳的音频转写
                    - 带时间戳或帧序列的 OCR 文本

                    你的职责是：
                    - 融合音频与 OCR 内容
                    - 利用时间戳重建结构与顺序
                    - 根据内容自动识别主题与重点
                    - 推断纠正 OCR 可能的错误
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
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"  ✗ Groq 总结失败: {e}")
        return f"[总结失败: {str(e)}]\n\n原始内容:\n{full_text}"


def generate_detailed_content(full_text: str) -> str:
    """
    生成详细的内容概括，包含更多细节。
    使用更大的token限制（12000）以产出更完整的内容。
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，跳过详细内容生成")
        return ""
    
    try:
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
        # 详细内容使用更大的token限制
        max_tokens = int(os.getenv("GROQ_DETAIL_MAX_TOKENS", "12000"))
        temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
        
        prompt = f"""
请基于以下视频的音频转写和OCR文本，生成一份**详细的内容概括**。

要求：
1. **逐段详细展开**：按视频的时间顺序，详细描述每个主要部分的内容
2. **保留关键细节**：
   - 具体的数字、数据、参数
   - 人名、地名、专业术语
   - 具体的操作步骤、流程
   - 引用的原话、关键句子
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

以下是原始内容：
{full_text[:50000]}
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": """你是一个专业的内容整理助手。你的任务是：
                    - 从视频转写和OCR文本中提取所有重要信息
                    - 生成详尽、完整的内容概括
                    - 保留原始内容中的关键细节和数据
                    - 使用清晰的结构组织信息
                    - 确保内容可以作为视频内容的完整参考"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"  ⚠️  详细内容生成失败: {e}")
        return ""


def merge_summary_with_details(summary: str, detailed_content: str) -> str:
    """
    将详细内容概括追加到报告末尾。
    保持原有报告内容不变。
    """
    if not detailed_content:
        return summary
    
    # 直接追加到末尾
    return summary + f"\n\n---\n\n## 📖 详细内容概括（完整版）\n\n{detailed_content}\n"


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
    timeline: list = None
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
    report.append("# 📹 视频分析报告\n")
    report.append(f"**📝 视频名称**: {video_name}  ")
    report.append(f"**🕒 处理时间**: {formatted_time}  ")
    report.append(f"**📁 输出目录**: `{session_dir.name}`  ")
    report.append(f"**🔧 处理模式**: {'完整模式 (OCR + 音频)' if with_frames else '音频模式'}  ")
    report.append("\n---\n")
    report.append("## 📊 数据统计\n")
    report.append(f"- **语音识别**: {transcript_chars} 字符, {transcript_lines} 行")
    if with_frames:
        report.append(f"- **OCR识别**: {ocr_chars} 字符, {ocr_lines} 行")
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
            ocr_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.OCR,
                content_text=ocr_text,
                file_path=str(session_dir / "ocr_raw.md"),
                model_name="paddleocr-v4",
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
):
    ensure_dir(output_dir)

    # 1. 创建带时间戳的输出文件夹
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_name = video_path.stem
    session_dir = output_dir / f"{video_name}_{timestamp}"
    ensure_dir(session_dir)
    
    # 2. 各类文件路径
    audio_path = session_dir / f"{video_name}.wav"
    frames_dir = session_dir / "frames"
    ocr_raw_path = session_dir / "ocr_raw.md"
    transcript_raw_path = session_dir / "transcript_raw.md"
    report_path = session_dir / "report.md"
    
    print(f"\n📁 输出目录: {session_dir}")
    print(f"   时间戳: {timestamp}\n")

    # 获取视频时长
    print(">> 获取视频时长...")
    video_duration = get_video_duration(video_path)
    print(f"   ⏱️  视频时长: {video_duration:.2f} 秒 ({int(video_duration // 60)}:{int(video_duration % 60):02d})")

    ocr_text = ""
    transcript_text = ""
    
    # 2. 如果是OCR模式，先处理视频帧和OCR
    if with_frames:
        print("\n" + "="*60)
        print("📹 第一步：处理视频帧 OCR")
        print("="*60)
        
        print(">> 抽帧中...")
        extract_frames(video_path, frames_dir, fps=1)

        print("\n>> OCR 处理中...")
        
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
            
            ocr_text = ocr_folder_parallel(
                str(frames_dir),
                min_score=0.3,
                num_workers=num_workers,
                use_preprocessing=True,
                hybrid_mode=True,
            )
        else:
            # 降级到单进程模式
            print(f">> 初始化 OCR (det={ocr_det_model}, rec={ocr_rec_model})...")
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
    
    # 保存语音识别原始结果（Markdown 格式，包含时间戳）
    if transcript_text.strip():
        print(f"   💾 保存语音识别原始结果: {transcript_raw_path.name}")
        transcript_markdown = f"# 🎤 语音识别原始数据\n\n"
        transcript_markdown += f"**识别时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n"
        transcript_markdown += f"**总字符数**: {len(transcript_text)}  \n"
        transcript_markdown += f"**识别模型**: Groq Whisper  \n"
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
        timeline = match_audio_with_frames(transcript_data, frames_dir, fps=1)
        timeline_path = session_dir / "timeline.md"
        generate_timeline_report(timeline, timeline_path)
        print(f"   💾 保存音画时间轴: {timeline_path.name}")

    # 5. 合并文本：音频文字 + OCR 结果
    combined_text_parts = [f"=== Audio Transcript ===\n{transcript_text}\n"]
    if with_frames:
        combined_text_parts.append(f"\n\n=== OCR from Frames ===\n{ocr_text}\n")

    combined_text = "\n".join(combined_text_parts)

    # 6. 第一次AI调用：生成结构化摘要报告
    print("\n>> 第一次AI调用：生成结构化摘要...")
    summary = summarize_with_gpt_oss_120b(combined_text)
    
    # 7. 第二次AI调用：生成详细内容概括（使用带时间戳的完整文本）
    print(">> 第二次AI调用：生成详细内容概括...")
    # 构建带时间戳的转写文本
    timestamped_text_parts = ["=== Audio Transcript with Timestamps ===\n"]
    if transcript_data.get('segments'):
        for seg in transcript_data['segments']:
            start_time = f"{int(seg['start']//60):02d}:{int(seg['start']%60):02d}"
            end_time = f"{int(seg['end']//60):02d}:{int(seg['end']%60):02d}"
            timestamped_text_parts.append(f"[{start_time} - {end_time}] {seg['text']}")
    else:
        timestamped_text_parts.append(transcript_text)
    
    if with_frames:
        timestamped_text_parts.append(f"\n\n=== OCR from Frames ===\n{ocr_text}\n")
    
    timestamped_combined_text = "\n".join(timestamped_text_parts)
    detailed_content = generate_detailed_content(timestamped_combined_text)
    
    # 8. 合并摘要和详细内容
    if detailed_content:
        print(">> 合并摘要与详细内容...")
        summary = merge_summary_with_details(summary, detailed_content)
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
        timeline=timeline
    )
    
    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n📄 报告已保存到: {report_path}")
    print(f"📁 完整输出目录: {session_dir}")
    
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
        help="PaddleOCR 语言（默认: ch）",
    )
    parser.add_argument(
        "--ocr-det-model",
        type=str,
        default="server",  # 改为 server 以获得更好的效果
        choices=["server", "mobile"],
        help="OCR 检测模型类型（默认: server，复杂背景建议使用）",
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
            print(f"✅ 下载完成: {video_path}")
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            exit(1)
    else:
        # 如果是本地文件路径
        video_path = Path(input_str).resolve()
        if not video_path.exists():
            print(f"❌ 错误：视频文件不存在: {video_path}")
            exit(1)

    output_dir = Path(args.out_dir).resolve()

    process_video(
        video_path=video_path,
        output_dir=output_dir,
        with_frames=args.with_frames,
        ocr_lang=args.ocr_lang,
        ocr_det_model=args.ocr_det_model,
        ocr_rec_model=args.ocr_rec_model,
        use_gpu=args.use_gpu,
        source_url=source_url,
        platform_title=platform_title,
    )


if __name__ == "__main__":
    main()
