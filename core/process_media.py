import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import glob
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

#region 文本处理辅助
def read_text_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"[读取文件错误: {e}]"

def get_latest_report(output_dir):
    # output_dir contains directories with timestamps, need to find the latest report.md
    out_path = Path(output_dir)
    if not out_path.exists():
        return ""
    
    subdirs = [d for d in out_path.iterdir() if d.is_dir()]
    if not subdirs:
        return ""
    
    # Sort by modification time
    latest_dir = max(subdirs, key=os.path.getmtime)
    report_file = latest_dir / "report.md"
    if report_file.exists():
        return read_text_file(report_file)
    return ""
#endregion

#region 媒体处理分发器
def process_file(file_path: Path, with_ocr: bool, unknown_args: list = None):
    if unknown_args is None:
        unknown_args = []
    
    ext = file_path.suffix.lower()
    
    # 文本或Markdown
    if ext in ['.txt', '.md']:
        print(f"📄 读取文本文件: {file_path}")
        return f"### 文件: {file_path.name}\n\n" + read_text_file(file_path)
    
    # 视频或音频
    elif ext in ['.mp4', '.mkv', '.mov', '.avi', '.mp3', '.wav', '.m4a']:
        is_video = ext in ['.mp4', '.mkv', '.mov', '.avi']
        type_str = "视频" if is_video else "音频"
        print(f"{'🎬' if is_video else '🎵'} 处理{type_str}: {file_path}")
        
        # Start core/process_video.py as subprocess
        cmd = [sys.executable, "core/process_video.py", str(file_path)]
        if with_ocr and is_video:
            cmd.append("--with-frames")
        if unknown_args:
            cmd.extend(unknown_args)
            
        try:
            # We don't want to flood the console, but we might want to capture stdout
            print(f"   => 正在通过 process_video.py 处理 {file_path} ... (请耐心等待)")
            subprocess.run(cmd, check=True)
            report = get_latest_report("output")
            return f"### {type_str}: {file_path.name}\n\n" + report
        except Exception as e:
            return f"### {type_str}: {file_path.name}\n\n处理失败: {e}"
            
    # 图片
    elif ext in ['.png', '.jpg', '.jpeg', '.webp']:
        if with_ocr:
            print(f"🖼️ OCR识别图片: {file_path}")
            try:
                import platform
                if platform.system() == 'Darwin':
                    from ocr.ocr_vision import ocr_folder_vision
                    tmp_dir = Path("output/tmp_img")
                    tmp_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Empty the tmp directory first to avoid old files
                    for old_f in tmp_dir.iterdir():
                         if old_f.is_file():
                             old_f.unlink()
                             
                    shutil.copy(file_path, tmp_dir / file_path.name)
                    res = ocr_folder_vision(str(tmp_dir))
                    return f"### 图片: {file_path.name}\n\nOCR内容:\n{res}"
                else:
                    return f"### 图片: {file_path.name}\n\n[目前OCR快速适配仅在使用 Apple Vision 的 macOS 上直接返回，其他系统请等待后续更新]"
            except Exception as e:
                 return f"### 图片: {file_path.name}\n\nOCR失败: {e}"
        else:
             return f"### 图片: {file_path.name}\n\n[无文本 (OCR未开启)]"

    return ""
#endregion

#region LLM整合与主流程
def summarize_all(content):
    print("🧠 正在请求 AI 对所有汇总内容进行深度分析与重新构排...")
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("未找到 GROQ_API_KEY，跳过AI润色，直接保存原始内容。")
        return content
        
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = f"你是一个专业的媒体内容分析与整合专家。以下内容来自于多个信息源（文本文件、音频/视频中的提录和总结、图片中的OCR识别文字）。请您对这些零散的内容进行统合，提取最为核心的信息、知识点与观点，并输出一篇结构严谨且易于阅读的综合长文总结。如果内容繁杂不相关，请分别列出各个子主题。\n\n【原始多媒体提取内容如下】:\n{content}"
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ AI 汇总失败: {e}\n保存原始提取内容。")
        return content

def main():
    parser = argparse.ArgumentParser(description="多媒体目录统一处理(支持音频/视频/图片/文字融合总结)")
    parser.add_argument("path", help="文件或目录路径 (支持单文件或文件夹)")
    parser.add_argument("--with-ocr", action="store_true", help="是否启用视觉OCR(针对视频/图片)")
    parser.add_argument("--with-frames", action="store_true", help="同 --with-ocr, 兼容Makefile老接口")
    args, unknown = parser.parse_known_args()
    
    use_ocr = args.with_ocr or args.with_frames

    target_path = Path(args.path)
    if not target_path.exists():
        print(f"❌ 路径不存在: {target_path}")
        sys.exit(1)

    # Output all final results to /docs/ as per MIAP protocol
    docs_dir = PROJECT_ROOT / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    results = []
    
    if target_path.is_file():
        res = process_file(target_path, use_ocr, unknown)
        if res: results.append(res)
    else:
        # Directory iteration
        extensions = {'.txt', '.md', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mkv', '.mov', '.avi', '.mp3', '.wav', '.m4a'}
        # Recursively find supported files
        found_files = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                fpath = Path(root) / f
                if fpath.suffix.lower() in extensions:
                    found_files.append(fpath)
                    
        # Sort to handle files in a somehow ordered manner
        found_files.sort()
        print(f"📂 在 {target_path} 中找到 {len(found_files)} 个支持的文件...")
        
        for fpath in found_files:
            res = process_file(fpath, use_ocr, unknown)
            if res: results.append(res)
                    
    combined_raw_text = "\n\n" + "="*40 + "\n\n".join(results)
    
    # 统一进行 AI 总结
    final_text = summarize_all(combined_raw_text)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = docs_dir / f"media_summary_{timestamp}.md"
    
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write("# 综合媒体知识抽取与汇总\n\n")
        f.write(final_text)
        f.write("\n\n---\n\n## 详细原始提取内容附录\n\n")
        f.write(combined_raw_text)
        
    print(f"✅ 处理完成！结果已保存在 {out_file} Nya～")

if __name__ == '__main__':
    main()
#endregion
