# process_video.py
import argparse
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

from ocr_utils import init_ocr, ocr_folder_to_text

# 可选：支持从 URL 直接下载
try:
    from video_downloader import VideoDownloader
    DOWNLOADER_AVAILABLE = True
except ImportError:
    DOWNLOADER_AVAILABLE = False

# 加载环境变量
load_dotenv()


# ========== 路径/目录处理 ==========
def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


# ========== ffmpeg: 音频 & 抽帧 ==========
def extract_audio(video_path: Path, audio_path: Path):
    """
    用 ffmpeg 从视频里分离音频，输出为 wav。
    """
    ensure_dir(audio_path.parent)
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",          # no video
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True)


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
def transcribe_audio_with_groq(audio_path: Path) -> dict:
    """
    使用 Groq 的 Whisper 模型进行语音转文字，返回带时间戳的数据。
    
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
        
        with open(audio_path, "rb") as audio_file:
            # 使用 verbose_json 格式获取时间戳信息
            transcription = client.audio.transcriptions.create(
                file=(audio_path.name, audio_file.read()),
                model=model,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        
        # 提取文本和时间戳片段
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

请将以下“带时间戳的音频转写 + OCR 文本”整理成一份**结构化 Markdown 知识档案**。

你需要：
1. **使用 Markdown** 输出（标题、列表、引用、表格等）
2. 按时间顺序梳理主要片段，并为关键内容标注对应时间戳
3. 合并音频与 OCR 内容：  
   - 如果 OCR 文字不完整，请根据上下文**推断合理含义**  
   - 如果某些屏幕文字重要（如 PPT、界面按钮、参数、代码），请单独提取并解释
4. 自动识别“主题/章节”并结构化总结：概念、步骤、场景、结论
5. 提取重要数据：数字、阈值、规则、引用、命令、日期等
6. 为未来检索生成若干关键词（tags）
7. 稍微详细一些，但不要写废话（重点是**可回溯、可搜索、可理解**）

推荐结构：
## 内容概览
## 时间线（关键片段 + 时间戳）
## 主题总结（自动生成主题名）
## 详细说明（合并音频与 OCR）
## OCR 信息与推断（列出重要屏幕文字并解释）
## 关键信息（数字、规则、参数）
## 关键句（含时间戳）
## 标签（tags）

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


# ========== 主控制流程 ==========
def process_video(
    video_path: Path,
    output_dir: Path,
    with_frames: bool = False,
    ocr_lang: str = "ch",
    ocr_det_model: str = "mobile",
    ocr_rec_model: str = "mobile",
    use_gpu: bool = False,
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

    ocr_text = ""
    transcript_text = ""
    
    # 2. 如果是OCR模式，先处理视频帧和OCR
    if with_frames:
        print("\n" + "="*60)
        print("📹 第一步：处理视频帧 OCR")
        print("="*60)
        
        print(">> 抽帧中...")
        extract_frames(video_path, frames_dir, fps=1)

        print(f"\n>> 初始化本地 OCR (det={ocr_det_model}, rec={ocr_rec_model})...")
        ocr = init_ocr(
            lang=ocr_lang,
            use_gpu=use_gpu,
            det_model=ocr_det_model,
            rec_model=ocr_rec_model
        )

        print("\n>> 对所有帧做 OCR（PP-OCRv4 Server + 预处理 + 混合模式）...")
        # 使用混合模式：同时识别底部字幕和画面其他文字
        ocr_text = ocr_folder_to_text(
            ocr, 
            str(frames_dir), 
            min_score=0.3,  # 识别阶段严格：只保留高置信度结果
            debug=False,
            use_preprocessing=True,  # 启用图像预处理（对比度+锐化）
            roi_bottom_only=True,    # 在单一模式下生效
            hybrid_mode=True,        # 【混合模式】同时识别字幕区和全画面
        )
        
        print()  # 空行
        if ocr_text.strip():
            char_count = len(ocr_text)
            line_count = ocr_text.count('\n')
            print(f"✅ OCR 完成！识别到 {char_count} 个字符，{line_count} 行文本")
            
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

    # 6. 调 GPT-OSS 120B 做总结（占位）
    print("\n>> 调用 GPT-OSS 120B 做总结（占位）...")
    summary = summarize_with_gpt_oss_120b(combined_text)

    # 7. 生成格式化报告
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
    )


if __name__ == "__main__":
    main()
