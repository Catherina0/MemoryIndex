"""
import_video.py - 轻量视频入库脚本

用途：对已下载的视频只做截图OCR + AI摘要/重命名 + 数据库入库，跳过音频转写和视频帧分析。
适合场景：音乐MV、无对话视频、只需归档不需分析的视频。

流程：
  1. 读取视频文件 + 同名截图
  2. 用 Vision OCR 识别截图内容（平台页面信息）
  3. 用 LLM 基于 OCR 内容生成简短摘要 + 文件夹名
  4. 写 output/<folder_name>/ 下的 README.md / summary.md
  5. 入库 VideoRepository
"""

import argparse
import os
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

# ── 导入 OCR（Vision 优先，macOS）─────────────────────────────────────────────
import platform
_init_vision_ocr = None
_ocr_folder_vision = None
try:
    from ocr.ocr_vision import init_vision_ocr as _init_vision_ocr, ocr_folder_vision as _ocr_folder_vision
except ImportError:
    pass

# ── 导入数据库────────────────────────────────────────────────────────────────
from db import VideoRepository
from db.models import Video, Artifact, SourceType, ArtifactType, ProcessingStatus

#region 工具函数

def _sanitize_name(name: str, max_len: int = 50) -> str:
    """清理字符串，使其适合作为文件夹名"""
    name = re.sub(r'["\'\n\r\t]', '', name)
    name = re.sub(r'[/\\<>:"|?*]', '_', name)
    name = name.strip().strip('._')
    if len(name) > max_len:
        name = name[:max_len]
    return name or "imported_video"


def _ocr_screenshot(screenshot_path: Path, session_dir: Path) -> str:
    """对截图做 Vision OCR，返回识别文本"""
    if not screenshot_path or not screenshot_path.exists():
        return ""
    if not _init_vision_ocr or not _ocr_folder_vision:
        print("   ⚠️  Vision OCR 不可用，跳过截图识别")
        return ""

    print(f"   🖼️  OCR 识别截图: {screenshot_path.name}")
    try:
        tmp_dir = session_dir / "_cover_tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        dest = tmp_dir / "frame_0001.png"
        if screenshot_path.suffix.lower() != ".png":
            from PIL import Image
            with Image.open(screenshot_path) as img:
                img.save(dest)
        else:
            shutil.copy(screenshot_path, dest)

        ocr_instance = _init_vision_ocr(lang="ch")
        text = _ocr_folder_vision(ocr_instance, tmp_dir, output_path=None, debug=False)

        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)

        print(f"   ✅ OCR 完成: {len(text)} 字符")
        return text
    except Exception as e:
        print(f"   ⚠️  OCR 失败: {e}")
        shutil.rmtree(session_dir / "_cover_tmp", ignore_errors=True)
        return ""


def _llm_generate_title_and_summary(
    video_title: str,
    ocr_text: str,
    uploader: str = "",
    duration: float = 0,
) -> tuple[str, str]:
    """
    调用 Groq LLM，根据截图 OCR + 原始标题生成：
    - folder_name: 简洁语义化文件夹名（≤30字符，下划线分隔）
    - summary: 一段简短的中文摘要（2-4句）

    Returns:
        (folder_name, summary)
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("   ⚠️  GROQ_API_KEY 未设置，使用原始标题作为文件夹名")
        return _sanitize_name(video_title), f"视频标题：{video_title}"

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        duration_str = ""
        if duration:
            m, s = divmod(int(duration), 60)
            h, m = divmod(m, 60)
            duration_str = f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"

        prompt = f"""你是一个个人知识库的内容整理助手。
我下载了一个视频，现在需要你帮我：
1. 生成一个简洁的文件夹名（≤30个字符，只能用字母/数字/中文/下划线，不能有空格和特殊符号）
2. 写一段简短的中文描述摘要（2-4句，说清楚这是什么内容，由谁上传，时长，适合什么场景使用）

视频原始标题：{video_title}
上传者：{uploader or '未知'}
时长：{duration_str or '未知'}
截图页面 OCR 内容（YouTube页面信息）：
{ocr_text[:1200] if ocr_text else '（无截图信息）'}

请严格按照以下 JSON 格式回复，不要有任何其他内容：
{{"folder_name": "...", "summary": "..."}}"""

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.4,
        )
        raw = response.choices[0].message.content.strip()

        # 提取 JSON
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            import json
            data = json.loads(json_match.group())
            folder_name = _sanitize_name(data.get("folder_name", video_title))
            summary = data.get("summary", "").strip() or f"视频标题：{video_title}"
            print(f"   ✅ LLM 生成文件夹名: {folder_name}")
            return folder_name, summary
        else:
            print(f"   ⚠️  LLM 回复格式异常，使用原始标题")
            return _sanitize_name(video_title), f"视频标题：{video_title}"

    except Exception as e:
        print(f"   ⚠️  LLM 调用失败: {e}")
        return _sanitize_name(video_title), f"视频标题：{video_title}"

#endregion


#region 主入库流程

def import_video(
    video_path: Path,
    output_dir: Path,
    source_url: str = None,
    platform_title: str = None,
    video_info: dict = None,
) -> int:
    """
    轻量入库：截图OCR → AI摘要+重命名 → 数据库入库

    Returns:
        int: 数据库视频 ID，失败返回 None
    """
    video_info = video_info or {}
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 基本信息 ─────────────────────────────────────────────────────────────
    video_name = video_path.stem
    title = platform_title or video_info.get("title") or video_name
    uploader = video_info.get("uploader", "")
    duration = video_info.get("duration") or 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n📹 视频: {video_path.name}")
    print(f"   标题: {title}")
    if uploader:
        print(f"   上传者: {uploader}")
    if duration:
        m, s = divmod(int(duration), 60)
        print(f"   时长: {m}m{s:02d}s ({int(duration)}秒)")

    # ── 查找截图 ──────────────────────────────────────────────────────────────
    screenshot_path = None
    for candidate in [
        video_path.parent / f"{video_path.stem}_screenshot.png",
        video_path.parent / f"{video_path.stem}_screenshot.jpg",
        video_path.with_suffix(".jpg"),
        video_path.with_suffix(".png"),
    ]:
        if candidate.exists():
            screenshot_path = candidate
            break

    # ── 创建临时 session 目录（用于 OCR 等中间产物）─────────────────────────
    tmp_session = output_dir / f"_import_tmp_{video_path.stem}"
    tmp_session.mkdir(parents=True, exist_ok=True)

    # ── OCR 截图 ──────────────────────────────────────────────────────────────
    ocr_text = _ocr_screenshot(screenshot_path, tmp_session)

    # ── LLM 生成文件夹名 + 摘要 ───────────────────────────────────────────────
    print("\n🧠 使用 LLM 生成语义化文件夹名和摘要...")
    folder_name, summary = _llm_generate_title_and_summary(
        video_title=title,
        ocr_text=ocr_text,
        uploader=uploader,
        duration=duration,
    )

    # ── 确认最终 session 目录（检查重名）──────────────────────────────────────
    final_session = output_dir / f"{folder_name}_{timestamp}"
    # 如果 output/<video_name> 已存在（download 阶段生成的 README.md），优先复用
    existing_session = output_dir / video_name
    if existing_session.exists() and not (existing_session / "report.md").exists():
        # 将已有目录重命名为新名字
        try:
            existing_session.rename(final_session)
            print(f"   ✅ 已有目录重命名: {existing_session.name} → {final_session.name}")
        except Exception:
            pass
    final_session.mkdir(parents=True, exist_ok=True)

    # ── 复制截图到 session 目录 ────────────────────────────────────────────────
    if screenshot_path and screenshot_path.exists():
        dest_screenshot = final_session / f"screenshot{screenshot_path.suffix}"
        if not dest_screenshot.exists():
            shutil.copy(screenshot_path, dest_screenshot)

    # ── 写 summary.md ─────────────────────────────────────────────────────────
    summary_path = final_session / "summary.md"
    summary_path.write_text(summary, encoding="utf-8")
    print(f"   ✅ 摘要已写入: {summary_path.name}")

    # ── 写 report.md（占位，标记为轻量导入）───────────────────────────────────
    report_path = final_session / "report.md"
    report_lines = [
        f"# {title}",
        "",
        f"**上传者**: {uploader or '未知'}",
        f"**时长**: {int(duration)}秒",
        f"**导入时间**: {timestamp}",
        f"**来源**: {source_url or '本地文件'}",
        "",
        "## 摘要",
        "",
        summary,
    ]
    if ocr_text:
        report_lines += ["", "## 页面截图 OCR", "", ocr_text[:3000]]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")

    # ── 清理临时目录 ──────────────────────────────────────────────────────────
    shutil.rmtree(tmp_session, ignore_errors=True)

    print(f"\n📁 输出目录: file://{final_session}")

    # ── 入库 ─────────────────────────────────────────────────────────────────
    print("\n💾 保存到数据库...")
    try:
        repo = VideoRepository()

        # 判断来源类型
        if source_url:
            if "youtube.com" in source_url or "youtu.be" in source_url:
                source_type = SourceType.YOUTUBE
            elif "bilibili.com" in source_url:
                source_type = SourceType.BILIBILI
            else:
                source_type = SourceType.URL
        else:
            source_type = SourceType.LOCAL

        content_hash = repo.calculate_content_hash(str(video_path))
        existing = repo.get_video_by_hash(content_hash)

        if existing:
            video_id = existing.id
            print(f"   ⚠️  视频已存在 (ID: {video_id})，更新元数据...")
            repo.update_video_metadata(
                video_id=video_id,
                duration_seconds=duration,
                title=title,
                platform_title=title,
            )
        else:
            video = Video(
                content_hash=content_hash,
                video_id=video_info.get("video_id"),
                source_type=source_type,
                source_url=source_url,
                platform_title=title,
                title=title,
                duration_seconds=duration,
                file_path=str(video_path),
                file_size_bytes=video_path.stat().st_size,
                processing_config={"import_mode": "lightweight", "output_dir": str(final_session)},
                status=ProcessingStatus.COMPLETED,
            )
            video_id = repo.create_video(video)
            print(f"   ✅ 创建视频记录 (ID: {video_id})")

        # 保存摘要 artifact
        if summary.strip():
            summary_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.SUMMARY,
                content_text=summary,
                file_path=str(summary_path),
                model_name="groq-llama3-70b",
                char_count=len(summary),
            )
            repo.save_artifact(summary_artifact)

        # 保存截图 OCR artifact
        if ocr_text.strip():
            ocr_artifact = Artifact(
                video_id=video_id,
                artifact_type=ArtifactType.OCR,
                content_text=ocr_text,
                file_path=str(final_session / "screenshot_ocr.md"),
                model_name="apple-vision-ocr",
                char_count=len(ocr_text),
            )
            # 顺便写出 screenshot_ocr.md
            (final_session / "screenshot_ocr.md").write_text(
                f"# 截图 OCR 内容\n\n{ocr_text}", encoding="utf-8"
            )
            repo.save_artifact(ocr_artifact)

        # 更新全文搜索索引
        print("   🔍 更新全文搜索索引...")
        repo.update_fts_index(video_id)

        print(f"   ✅ 入库完成！(视频ID: {video_id})")
        print(f"   💡 使用 `make search Q=\"{folder_name[:10]}\"` 搜索")

        return video_id

    except Exception as e:
        print(f"   ❌ 数据库保存失败: {e}")
        import traceback
        traceback.print_exc()
        return None

#endregion


#region CLI 入口

def _download_from_url(url: str, download_dir: str = "videos", force: bool = False):
    """
    调用 VideoDownloader 下载视频，返回 (video_path, video_info, source_url)
    """
    try:
        from core.video_downloader import VideoDownloader
    except ImportError:
        print("❌ video_downloader 模块不可用，请检查依赖")
        sys.exit(1)

    downloader = VideoDownloader(download_dir=download_dir)
    print(f"📥 准备下载: {url}")
    file_info = downloader.download_video(url, force_redownload=force)

    video_info = {
        "title": getattr(file_info, "title", None),
        "video_id": getattr(file_info, "video_id", None),
        "platform": getattr(file_info, "platform", None),
        "duration": getattr(file_info, "duration", None),
        "uploader": getattr(file_info, "uploader", None),
        "upload_date": getattr(file_info, "upload_date", None),
        "url": url,
    }
    return file_info.file_path, video_info, url


def _extract_video_url_from_input(input_text: str) -> str | None:
    """
    从 URL 或平台分享文本中提取可下载的视频 URL。

    复用 video_downloader 的解析规则，保证 make download 与下载器 CLI 行为一致。
    """
    try:
        from core.video_downloader import extract_url_from_text
    except ImportError:
        return None

    return extract_url_from_text(input_text)


def main():
    parser = argparse.ArgumentParser(
        description="轻量视频入库：截图OCR + AI摘要 + 重命名 + 入库（跳过音频/视频帧分析）\n支持 URL 直接下载后入库，也支持已下载文件路径输入。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  # 直接从 URL 下载并入库
  python core/import_video.py https://www.youtube.com/watch?v=xxx
  # 对已下载文件入库
  python core/import_video.py videos/my_music.mp4
  python core/import_video.py videos/my_music.mp4 --url https://youtube.com/watch?v=xxx
        """,
    )
    parser.add_argument("video", help="视频文件路径 或 视频 URL（自动下载）")
    parser.add_argument("--url", default=None, help="来源 URL（仅路径模式时用于记录来源，URL 模式下无需填）")
    parser.add_argument("--title", default=None, help="视频标题（可选，覆盖自动检测）")
    parser.add_argument("--out-dir", default="output", help="输出根目录（默认: output/）")
    parser.add_argument("--download-dir", default="videos", help="视频下载目录（默认: videos/）")
    parser.add_argument("--force", action="store_true", help="强制重新下载（URL 模式下有效）")
    args = parser.parse_args()

    output_dir = Path(args.out_dir).resolve()

    # ── 判断输入是 URL 还是文件路径 ───────────────────────────────────────────
    input_str = args.video
    extracted_url = _extract_video_url_from_input(input_str)
    is_url = extracted_url is not None

    if is_url:
        # URL 模式：先下载再入库
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📥 下载并轻量入库")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if extracted_url != input_str:
            print(f"🔗 已从输入文本提取 URL: {extracted_url}")
        video_path, video_info, source_url = _download_from_url(
            url=extracted_url,
            download_dir=args.download_dir,
            force=args.force,
        )
        platform_title = args.title or video_info.get("title")
    else:
        # 文件路径模式
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📥 轻量视频入库（跳过音频/帧分析）")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        video_path = Path(input_str).resolve()
        if not video_path.exists():
            print(f"❌ 文件不存在: {video_path}")
            sys.exit(1)
        source_url = args.url

        # 尝试从同目录的 output/<stem>/README.md 读取元数据
        video_info = {}
        readme_path = output_dir / video_path.stem / "README.md"
        if readme_path.exists():
            import re as _re
            text = readme_path.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if line.startswith("- **标题**"):
                    m = _re.search(r'\*\*标题\*\*[:：]\s*(.+)', line)
                    if m and not video_info.get("title"):
                        video_info["title"] = m.group(1).strip()
                elif "duration" in line.lower():
                    m = _re.search(r'(\d+)\s*秒', line)
                    if m and not video_info.get("duration"):
                        video_info["duration"] = float(m.group(1))
                elif line.startswith("- **上传者**"):
                    m = _re.search(r'\*\*上传者\*\*[:：]\s*(.+)', line)
                    if m and not video_info.get("uploader"):
                        video_info["uploader"] = m.group(1).strip()

        platform_title = args.title or video_info.get("title")

    import_video(
        video_path=video_path,
        output_dir=output_dir,
        source_url=source_url,
        platform_title=platform_title,
        video_info=video_info,
    )

    print("\n✅ 完成！")


if __name__ == "__main__":
    main()

#endregion



if __name__ == "__main__":
    main()

#endregion
