# process_video.py
import argparse
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

from ocr_utils import init_ocr, ocr_folder_to_text

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
    用 ffmpeg 抽帧：默认 1 fps，可以后面再调。
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


# ========== Groq API 集成 ==========
def transcribe_audio_with_groq(audio_path: Path) -> str:
    """
    使用 Groq 的 Whisper 模型进行语音转文字。
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("  ⚠️  GROQ_API_KEY 未设置，使用占位符")
        return f"[FAKE TRANSCRIPT for {audio_path.name}] 请在 .env 中设置 GROQ_API_KEY"
    
    try:
        client = Groq(api_key=api_key)
        model = os.getenv("GROQ_ASR_MODEL", "whisper-large-v3-turbo")
        
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(audio_path.name, audio_file.read()),
                model=model,
                response_format="text",
            )
        
        return transcription
    except Exception as e:
        print(f"  ✗ Groq 转写失败: {e}")
        return f"[转写失败: {str(e)}]"


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
        
        prompt = f"""请对以下内容进行详细的总结分析：

内容：
{full_text[:40000]}  # 提升输入长度限制

要求：
1. **使用完整的 Markdown 格式输出**（标题、列表、加粗、代码块等）
2. 提取核心要点和关键信息
3. 列出重要的数字、引用、时间点和事实
4. 按逻辑结构组织内容（使用 ## 标题分节）
5. 如果有 OCR 内容，重点分析屏幕文字和视觉信息
6. 如果有多个主题，分别总结
7. 输出要详细完整，不要过度精简
8. 分析和推理一些OCR识别的文本可能存在的含义和背景
9. 列出关键句子和段落便于回忆

输出格式示例：
## 📋 内容概述
[一句话概括主要内容]

## 🔑 核心要点
- 要点1
- 要点2
- 要点3

## 📊 详细内容
### 主题1
[详细说明...]

### 主题2
[详细说明...]

## 💡 关键信息
- 重要数字、时间、引用等

请用中文回答，充分利用 token 限制输出详细内容。"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的内容分析助手，擅长从视频转写和屏幕文字中提取关键信息并用结构化的 Markdown 格式呈现。你的总结应该详细、完整、易读。"
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


def generate_formatted_report(
    video_name: str,
    timestamp: str,
    transcript_text: str,
    ocr_text: str,
    summary: str,
    with_frames: bool,
    session_dir: Path
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

    # 4. Groq 语音转文字（占位）
    print(">> 调用 Groq 语音转写（占位）...")
    transcript_text = transcribe_audio_with_groq(audio_path)
    
    # 保存语音识别原始结果（Markdown 格式）
    if transcript_text.strip():
        print(f"   💾 保存语音识别原始结果: {transcript_raw_path.name}")
        transcript_markdown = f"# 🎤 语音识别原始数据\n\n"
        transcript_markdown += f"**识别时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n"
        transcript_markdown += f"**总字符数**: {len(transcript_text)}  \n"
        transcript_markdown += f"**识别模型**: Groq Whisper  \n\n"
        transcript_markdown += "---\n\n"
        transcript_markdown += "## 📝 转写内容\n\n"
        transcript_markdown += transcript_text
        transcript_raw_path.write_text(transcript_markdown, encoding="utf-8")

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
        session_dir=session_dir
    )
    
    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n📄 报告已保存到: {report_path}")
    print(f"📁 完整输出目录: {session_dir}")


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(description="Video → Text Report pipeline")
    parser.add_argument("video", type=str, help="输入视频路径")
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

    args = parser.parse_args()

    video_path = Path(args.video).resolve()
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
