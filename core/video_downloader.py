"""
video_downloader.py - 统一视频下载层

支持多平台视频下载：
- YouTube, Bilibili, 小红书等
- 自动降级策略：yt-dlp → BBDown → XHS-Downloader
- 统一输出格式和存储路径
"""

import os
import re
import json
import subprocess
import shutil
import sys
import warnings
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

# 忽略第三方库的警告（如 requests 的 urllib3 版本警告）
warnings.filterwarnings("ignore", category=UserWarning, module="requests")
# 也可以忽略专门针对 urllib3 的特定警告
try:
    import requests
    from requests.packages.urllib3.exceptions import DependencyWarning
    warnings.filterwarnings("ignore", category=DependencyWarning)
except ImportError:
    pass

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  提示：安装 tqdm 可显示下载进度条 (pip install tqdm)")


@dataclass
class LocalFileInfo:
    """下载后的本地文件信息"""
    file_path: Path           # 本地文件路径
    platform: str             # 平台名称 (youtube, bilibili, xiaohongshu)
    video_id: str             # 视频ID
    title: str                # 视频标题
    duration: Optional[float] # 时长（秒）
    uploader: Optional[str]   # 上传者
    upload_date: Optional[str] # 上传日期
    metadata: Dict[str, Any]  # 其他元数据
    screenshot_path: Optional[Path] = None  # 截图路径


class VideoDownloader:
    """统一视频下载器"""
    
    def __init__(self, download_dir: str = "videos", json_mode: bool = False):
        """
        初始化下载器
        
        Args:
            download_dir: 视频下载目录，默认为 videos/
            json_mode: 是否为 JSON 模式（所有提示信息输出到 stderr）
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.json_mode = json_mode
        
        # 查找系统中的工具路径
        self.ytdlp_path = self._find_executable("yt-dlp")
        self.bbdown_path = self._find_executable("BBDown")
        self.xhs_path = self._find_executable("XHS-Downloader")
    
    def _find_executable(self, name: str) -> Optional[str]:
        """
        查找可执行文件路径（支持虚拟环境）
        
        Args:
            name: 可执行文件名
            
        Returns:
            完整路径或 None
        """
        # 首先尝试在虚拟环境中查找
        venv_path = None
        if hasattr(sys.modules.get('__main__'), '__file__'):
            base_path = Path(sys.modules['__main__'].__file__).parent
            venv_bin = base_path / ".venv" / "bin" / name
            if venv_bin.exists():
                return str(venv_bin)
        
        # 使用 shutil.which 在系统 PATH 中查找
        path = shutil.which(name)
        if path:
            return path
        
        return None
    
    def _extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """
        从URL中提取视频ID
        
        Args:
            url: 视频URL
            platform: 平台名称
            
        Returns:
            视频ID或None
        """
        if platform == "bilibili":
            # BV号
            bv_match = re.search(r'(BV[\w]+)', url)
            if bv_match:
                return bv_match.group(1)
            # av号
            av_match = re.search(r'av(\d+)', url)
            if av_match:
                return f"av{av_match.group(1)}"
        elif platform == "youtube":
            # YouTube视频ID
            yt_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
            if yt_match:
                return yt_match.group(1)
        elif platform == "xiaohongshu":
            # 小红书笔记ID
            xhs_match = re.search(r'/(?:explore|discovery/item)/([a-zA-Z0-9]+)', url)
            if xhs_match:
                return xhs_match.group(1)
        
        return None
    
    def check_already_downloaded(self, url: str) -> Optional[dict]:
        """
        检查视频是否已在数据库中存在
        
        Args:
            url: 视频URL
            
        Returns:
            如果已存在，返回 {'video_id': id, 'title': title, 'file_path': path}
            否则返回 None
        """
        try:
            from db import VideoRepository
            repo = VideoRepository()
            
            platform = self._detect_platform(url)
            video_id = self._extract_video_id(url, platform)
            
            # 先尝试通过视频ID查找
            if video_id:
                existing = repo.get_video_by_video_id(platform, video_id)
                if existing:
                    return {
                        'video_id': existing.id,
                        'title': existing.title,
                        'file_path': existing.file_path,
                        'source_url': existing.source_url
                    }
            
            # 再尝试通过完整URL查找
            existing = repo.get_video_by_source_url(url)
            if existing:
                return {
                    'video_id': existing.id,
                    'title': existing.title,
                    'file_path': existing.file_path,
                    'source_url': existing.source_url
                }
            
            return None
        except Exception as e:
            # 数据库不可用时不影响下载
            print(f"⚠️  检查数据库时出错: {e}", file=sys.stderr)
            return None
    
    def _capture_screenshot(self, url: str, output_path: Path):
        """
        使用 DrissionArchiver 截取网页截图 (支持 Cookie 和反爬策略)
        """
        output_stream = sys.stderr if self.json_mode else sys.stdout
        
        try:
            # 尝试导入 archiver 模块
            # 如果在 process_video.py 环境中运行，路径通常已正确设置
            # 如果单独运行，可能需要添加路径
            PROJECT_ROOT = Path(__file__).parent.parent
            if str(PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(PROJECT_ROOT))
            
            from archiver.core.drission_crawler import DrissionArchiver
            
            print(f"📸 正在调用浏览器截取网页...", file=output_stream, flush=True)
            
            # 初始化 Archiver (复用 browser_data 目录)
            browser_data_dir = PROJECT_ROOT / "browser_data"
            archiver = DrissionArchiver(
                output_dir=str(output_path.parent),
                browser_data_dir=str(browser_data_dir),
                headless=True,
                verbose=False
            )
            
            # 调用截图方法
            archiver.capture_screenshot(url, output_path)
            
            if output_path.exists():
                print(f"✅ 网页截图已保存: {output_path.name}", file=output_stream, flush=True)
            
        except ImportError:
            print(f"⚠️  未找到 archiver 模块，尝试使用基础 DrissionPage 截图...", file=output_stream, flush=True)
            self._capture_screenshot_basic(url, output_path)
            
        except Exception as e:
            print(f"⚠️  截图过程出错 (不影响视频下载): {e}", file=output_stream, flush=True)

    def _capture_screenshot_basic(self, url: str, output_path: Path):
        """基础版截图 (不带 Cookie 和复杂策略)"""
        output_stream = sys.stderr if self.json_mode else sys.stdout
        
        try:
            from DrissionPage import Chromium, ChromiumOptions
            
            co = ChromiumOptions()
            co.set_headless(True)
            co.set_argument('--no-sandbox')
            co.set_argument('--disable-gpu')
            
            browser = Chromium(co)
            tab = browser.new_tab(url)
            
            # 等待页面加载
            tab.wait.load_complete(timeout=30)
            target_platform = self._detect_platform(url)
            
            # 简单滚动
            tab.scroll.to_bottom()
            import time
            time.sleep(2)
            tab.scroll.to_top()
            time.sleep(1)
            
            # 截图
            tab.get_screenshot(path=str(output_path), full_page=True)
            
            tab.close()
            browser.quit()
            
            if output_path.exists():
                print(f"✅ (基础) 截图已保存: {output_path.name}", file=output_stream, flush=True)
            
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️  基础截图失败: {e}", file=output_stream, flush=True)

    def _save_metadata(self, file_info: LocalFileInfo, url: str):
        """保存视频元数据到 Markdown 文件"""
        try:
            # 目标目录: output/<视频文件名(无后缀)>/
            # 基于视频文件名（在 videos/ 下）创建 output 目录下的同名文件夹
            video_stem = file_info.file_path.stem
            output_dir = Path("output") / video_stem
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 使用 README.md 作为文件名
            md_path = output_dir / "README.md"
            
            # 准备数据            
            title = file_info.title or "Untitled"
            platform = file_info.platform or "unknown"
            video_id = file_info.video_id or "unknown"
            
            duration_str = "Unknown"
            if file_info.duration:
                duration_str = f"{file_info.duration:.1f}"
            
            uploader = file_info.uploader or "Unknown"
            upload_date = file_info.upload_date or "Unknown"
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            description = ""
            if file_info.metadata:
                description = file_info.metadata.get('description', '')
                
            if description:
                # 简单清理一下 description
                description = f"\n\n## 📝 简介\n\n{description}"
            
            # 使用 json.dumps 确保 YAML 字符串转义正确
            safe_title = json.dumps(title, ensure_ascii=False)
            safe_url = json.dumps(url, ensure_ascii=False)
            safe_platform = json.dumps(platform, ensure_ascii=False)
            safe_video_id = json.dumps(video_id, ensure_ascii=False)
            safe_uploader = json.dumps(uploader, ensure_ascii=False)
            safe_upload_date = json.dumps(upload_date, ensure_ascii=False)
            safe_now = json.dumps(now, ensure_ascii=False)

            # 更新文件路径引用为相对路径（因为 videos/ 和 output/ 平级）
            # videos/abc.mp4 -> ../../videos/abc.mp4 (如果在 output/abc/ 下)
            # 或者简单地引用绝对路径？或者仅文件名
            # 为了方便在 output/abc/ 下点击，最好使用相对路径
            # output/abc/ -> videos/abc.mp4
            # 相对路径: ../../videos/abc.mp4
            try:
                # 尝试计算相对路径
                video_rel_path = os.path.relpath(file_info.file_path, output_dir)
            except ValueError:
                # 如果跨驱动器等无法计算相对路径，使用绝对路径
                video_rel_path = str(file_info.file_path.absolute())

            md_content = f"""---
title: {safe_title}
url: {safe_url}
platform: {safe_platform}
video_id: {safe_video_id}
duration: {file_info.duration or 0}
uploader: {safe_uploader}
upload_date: {safe_upload_date}
downloaded_at: {safe_now}
---

# {title}

**来源**: [{url}]({url})  
**平台**: {platform}  
**视频ID**: {video_id}  
**时长**: {duration_str} 秒  
**上传者**: {uploader}  
**上传日期**: {upload_date}  
**下载时间**: {now}

---

## 📄 视频文件

文件路径: [{file_info.file_path.name}]({video_rel_path})
{description}

> 💡 **提示**: 此文件由 MemoryIndex 下载器自动生成
"""
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            # 仅在非JSON模式下打印，或者是使用 stderr
            output_stream = sys.stderr if self.json_mode else sys.stdout
            print(f"✅ 元数据已保存: {md_path}", file=output_stream, flush=True)
            
        except Exception as e:
            output_stream = sys.stderr if self.json_mode else sys.stdout
            print(f"⚠️  保存元数据失败: {e}", file=output_stream, flush=True)

    def download_video(self, url: str, force_redownload: bool = False) -> LocalFileInfo:
        """
        统一下载接口
        
        Args:
            url: 视频URL
            force_redownload: 是否强制重新下载（即使文件已存在）
            
        Returns:
            LocalFileInfo: 下载后的文件信息
            
        Raises:
            Exception: 下载失败时抛出异常
        """
        # 在 JSON 模式下，所有提示信息输出到 stderr
        output_stream = sys.stderr if self.json_mode else sys.stdout
        
        print(f"📥 准备下载视频: {url}", file=output_stream, flush=True)
        
        # 检测平台
        platform = self._detect_platform(url)
        print(f"🔍 检测到平台: {platform}", file=output_stream, flush=True)
        
        result = None
        
        # 检查数据库中是否已存在
        if not force_redownload:
            existing = self.check_already_downloaded(url)
            if existing:
                print(f"✅ 视频已在数据库中 (ID: {existing['video_id']})", file=output_stream, flush=True)
                print(f"   标题: {existing['title']}", file=output_stream, flush=True)
                print(f"   文件: {existing['file_path']}", file=output_stream, flush=True)
                print(f"💡 如需重新下载，请使用 force_redownload=True", file=output_stream, flush=True)
                
                # 检查文件是否仍然存在
                if existing['file_path'] and Path(existing['file_path']).exists():
                    # 返回已存在的文件信息
                    result = LocalFileInfo(
                        file_path=Path(existing['file_path']),
                        platform=platform,
                        video_id=self._extract_video_id(url, platform) or "unknown",
                        title=existing['title'],
                        duration=None,
                        uploader=None,
                        upload_date=None,
                        metadata={'already_downloaded': True, 'database_id': existing['video_id']}
                    )
                else:
                    print(f"⚠️  原文件已不存在，将重新下载", flush=True)
        
        if result is None:
            # 尝试下载
            try:
                # 1. 首选方案：yt-dlp（支持大多数平台）
                result = self._download_with_ytdlp(url, platform, force_redownload)
            except Exception as e:
                print(f"⚠️  yt-dlp 下载失败: {e}", file=output_stream, flush=True)
                
                # 2. B站降级方案：BBDown
                if platform == "bilibili":
                    try:
                        print("🔄 尝试使用 BBDown 下载...", file=output_stream, flush=True)
                        result = self._download_with_bbdown(url, force_redownload)
                    except Exception as e2:
                        print(f"❌ BBDown 下载失败: {e2}", file=output_stream, flush=True)
                        raise Exception(f"B站视频下载失败（已尝试 yt-dlp 和 BBDown）")
                
                # 3. 小红书降级方案：XHS-Downloader
                elif platform == "xiaohongshu":
                    try:
                        print("🔄 尝试使用 XHS-Downloader 下载...", file=output_stream, flush=True)
                        result = self._download_with_xhs(url, force_redownload)
                    except Exception as e2:
                        print(f"❌ XHS-Downloader 下载失败: {e2}", file=output_stream, flush=True)
                        raise Exception(f"小红书视频下载失败（已尝试 yt-dlp 和 XHS-Downloader）")
                
                # 其他平台直接抛出异常
            if result is None:
                 raise Exception(f"{platform} 平台视频下载失败")

        # 尝试截图 (如果文件已存在但没有截图，也可以补截图)
        if result and result.file_path:
            try:
                # 截图文件名: 视频文件名_screenshot.png
                screenshot_path = result.file_path.parent / f"{result.file_path.stem}_screenshot.png"
                if not screenshot_path.exists() or force_redownload:
                    self._capture_screenshot(url, screenshot_path)
                
                if screenshot_path.exists():
                    result.screenshot_path = screenshot_path
            except Exception as e:
                print(f"⚠️  截图步骤异常（不影响视频下载）: {e}", file=output_stream, flush=True)

        # 保存元数据 Markdown
        if result and result.file_path:
             self._save_metadata(result, url)

        return result

    
    def _detect_platform(self, url: str) -> str:
        """检测视频平台"""
        url_lower = url.lower()
        
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "bilibili.com" in url_lower or "b23.tv" in url_lower:
            return "bilibili"
        elif "xiaohongshu.com" in url_lower or "xhslink.com" in url_lower:
            return "xiaohongshu"
        elif "douyin.com" in url_lower:
            return "douyin"
        elif "tiktok.com" in url_lower:
            return "tiktok"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        else:
            return "unknown"
    
    def _download_with_progress(self, cmd: list, total_size: Optional[int] = None):
        """
        使用进度条执行下载命令

        Args:
            cmd: 下载命令列表
            total_size: 文件总大小（字节），如果已知
        """
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # 进度条始终创建（输出到 stderr，不影响 stdout 重定向）
        if total_size:
            # 已知文件大小：字节模式进度条
            pbar = tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc='下载进度',
                file=sys.stderr,
                dynamic_ncols=True,
            )
            last_downloaded = 0
            last_percent = 0.0
        else:
            # 未知文件大小：百分比模式进度条（0-100%）
            pbar = tqdm(
                total=100,
                unit='%',
                desc='下载进度',
                file=sys.stderr,
                dynamic_ncols=True,
                bar_format='{l_bar}{bar}| {n:.0f}%{postfix}',
            )
            last_percent = 0.0
            last_downloaded = 0

        for line in process.stdout:
            line = line.rstrip()
            if not line:
                continue

            # yt-dlp 进度行格式: [download]  45.8% of 123.45MiB at 1.23MiB/s ETA 00:23
            if '[download]' in line and '%' in line:
                match = re.search(r'([\d.]+)%', line)
                if match:
                    percent = float(match.group(1))
                    if total_size:
                        # 字节模式：按百分比换算已下载字节数
                        downloaded = int(total_size * percent / 100)
                        if downloaded > last_downloaded:
                            pbar.update(downloaded - last_downloaded)
                            last_downloaded = downloaded
                    else:
                        # 百分比模式：直接更新百分比增量
                        delta = percent - last_percent
                        if delta > 0:
                            pbar.update(delta)
                            last_percent = percent
                    # 在进度条后附加速度/ETA 信息
                    speed_match = re.search(r'at\s+([\d.]+\w+/s)', line)
                    eta_match = re.search(r'ETA\s+(\S+)', line)
                    postfix = {}
                    if speed_match:
                        postfix['速度'] = speed_match.group(1)
                    if eta_match:
                        postfix['ETA'] = eta_match.group(1)
                    if postfix:
                        pbar.set_postfix(postfix, refresh=False)
            elif '[download] Destination:' in line:
                # 显示目标文件路径（在进度条上方打印）
                tqdm.write(line, file=sys.stderr)
            elif line.startswith('[') and not line.startswith('[download]'):
                # 显示其他 yt-dlp 信息行（如 [youtube], [info], [Merger] 等）
                tqdm.write(line, file=sys.stderr)

        # 确保进度条跑满到100%
        if total_size and last_downloaded < total_size:
            pbar.update(total_size - last_downloaded)
        elif not total_size and last_percent < 100:
            pbar.update(100 - last_percent)

        pbar.close()

        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd)
    
    def _sanitize_filename(self, filename: str, max_length: int = 100) -> str:
        """
        清洗文件名，移除非法字符
        
        Args:
            filename: 原始文件名
            max_length: 最大长度
            
        Returns:
            清洗后的文件名
        """
        import unicodedata
        
        # 1. 规范化 Unicode（分解组合字符）
        filename = unicodedata.normalize('NFKC', filename)
        
        # 2. 只保留安全字符：字母、数字、中日韩文字、基本标点
        safe_chars = []
        for char in filename:
            code_point = ord(char)
            # 允许的字符范围：
            # - ASCII 可见字符（除了文件系统非法字符）
            # - 中日韩统一表意文字 (CJK Unified Ideographs): U+4E00 - U+9FFF
            # - 中日韩扩展A: U+3400 - U+4DBF
            # - 日文平假名: U+3040 - U+309F
            # - 日文片假名: U+30A0 - U+30FF
            # - 韩文音节: U+AC00 - U+D7AF
            if (32 <= code_point < 127 and char not in '<>:"/\\|?*') or \
               (0x4E00 <= code_point <= 0x9FFF) or \
               (0x3400 <= code_point <= 0x4DBF) or \
               (0x3040 <= code_point <= 0x309F) or \
               (0x30A0 <= code_point <= 0x30FF) or \
               (0xAC00 <= code_point <= 0xD7AF):
                safe_chars.append(char)
        
        filename = ''.join(safe_chars)
        
        # 3. 压缩连续空白字符为单个下划线
        filename = re.sub(r'[\s]+', '_', filename)
        
        # 4. 移除前后的点、空格和下划线
        filename = filename.strip('._\u3000 ')  # \u3000 是全角空格
        
        # 5. 截断过长的文件名（考虑 UTF-8 字节长度）
        if len(filename.encode('utf-8')) > max_length:
            # 按字符逐步截断直到满足字节长度要求
            while len(filename.encode('utf-8')) > max_length and len(filename) > 0:
                filename = filename[:-1]
            filename = filename.rstrip('._\u3000 ')
        
        return filename or "video"
    
    def _download_with_ytdlp(self, url: str, platform: str, force_redownload: bool) -> LocalFileInfo:
        """
        使用 yt-dlp Python 库下载视频（支持实时进度条）

        Args:
            url: 视频URL
            platform: 平台名称
            force_redownload: 是否强制重新下载

        Returns:
            LocalFileInfo: 下载后的文件信息
        """
        try:
            import yt_dlp
        except ImportError:
            raise Exception("yt-dlp Python 库未安装，请执行: pip install yt-dlp")

        # 在 JSON 模式下，所有提示信息输出到 stderr
        output_stream = sys.stderr if self.json_mode else sys.stdout

        # ── 进度条状态（在 progress_hook 闭包中共享） ──────────────────────
        _state = {
            "pbar": None,           # 当前活跃进度条
            "cur_file": None,       # 当前正在下载的文件名 (None 表示尚未开始)
            "last_bytes": 0,        # 上次已下载字节数（用于增量更新）
        }

        def _make_pbar(desc: str, total: Optional[int]):
            """创建一个新的 tqdm 进度条"""
            if not TQDM_AVAILABLE:
                return None
            # 强制刷新 stderr 缓冲区
            sys.stderr.flush()
            common = dict(
                desc=desc,
                file=sys.stderr,
                dynamic_ncols=True,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                leave=True, # 保留进度条
                miniters=1, # 频繁更新
            )
            if total:
                return tqdm(total=total, **common)
            else:
                return tqdm(**common)

        def progress_hook(d: dict):
            status = d.get("status")
            # 确保获取到一个显示名称，即使 filename 为空
            raw_fn = d.get("filename")
            filename = os.path.basename(raw_fn) if raw_fn else "downloading_video"

            if status == "downloading":
                total     = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                speed     = d.get("speed")       # bytes/s
                eta       = d.get("eta")          # seconds

                # 新文件开始下载时，或是首次创建进度条
                current_file = _state["cur_file"]
                if current_file is None or filename != current_file:
                    if _state["pbar"] is not None:
                        _state["pbar"].close()
                        sys.stderr.flush()
                    _state["cur_file"]  = filename
                    _state["last_bytes"] = 0
                    
                    label = filename if len(filename) <= 30 else f"…{filename[-29:]}"
                    _state["pbar"] = _make_pbar(f"下载 {label}", total)

                pbar = _state["pbar"]
                if pbar is not None:
                    # 如果这好像是一个新的total，重置进度条
                    if total and pbar.total is not None and abs(pbar.total - total) > 1024:
                        pbar.reset(total=total)
                        _state["last_bytes"] = 0
                        downloaded = d.get("downloaded_bytes", 0)

                    # 用增量更新，避免因估算值跳动导致进度条倒退
                    if downloaded > _state["last_bytes"]:
                        delta = downloaded - _state["last_bytes"]
                        pbar.update(delta)
                        _state["last_bytes"] = downloaded
                    
                    # 附加速度 / ETA 信息
                    postfix = {}
                    if speed and speed > 0:
                        postfix["速度"] = f"{speed / 1024 / 1024:.2f} MB/s"
                    if eta is not None:
                        m, s = divmod(int(eta), 60)
                        postfix["ETA"] = f"{m:02d}:{s:02d}"
                    if postfix:
                        # refresh=True 强制尽快刷新显示
                        pbar.set_postfix(postfix, refresh=True)

            elif status == "finished":
                pbar = _state["pbar"]
                if pbar is not None:
                    # 补足到 total（避免因估算误差导致进度条停在 99%）
                    if pbar.total and pbar.n < pbar.total:
                        pbar.update(pbar.total - pbar.n)
                    pbar.close()
                    sys.stderr.flush()
                _state["pbar"]      = None
                _state["cur_file"]  = None
                _state["last_bytes"] = 0

            elif status == "error":
                if _state["pbar"] is not None:
                    _state["pbar"].close()
                    sys.stderr.flush()
                    _state["pbar"] = None

        # ── 第一步：仅获取元数据（不下载） ────────────────────────────────
        print("📋 获取视频信息...", file=output_stream, flush=True)
        info_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        video_id   = info.get("id", "unknown")
        title      = self._sanitize_filename(info.get("title", "video"))
        duration   = info.get("duration")
        uploader   = info.get("uploader")
        upload_date = info.get("upload_date")
        filesize   = info.get("filesize") or info.get("filesize_approx")

        if filesize:
            print(f"📦 文件大小: {filesize / 1024 / 1024:.1f} MB", file=output_stream, flush=True)

        # ── 构造输出路径 ────────────────────────────────────────────────────
        filename    = f"{title}_{platform}_{video_id}.mp4"
        output_path = self.download_dir / filename

        if output_path.exists() and not force_redownload:
            print(f"✅ 文件已存在，跳过下载: {output_path}", file=output_stream, flush=True)
            return LocalFileInfo(
                file_path=output_path,
                platform=platform,
                video_id=video_id,
                title=info.get("title", ""),
                duration=duration,
                uploader=uploader,
                upload_date=upload_date,
                metadata=info,
            )

        # ── 第二步：下载（带实时进度回调） ────────────────────────────────
        print(f"⬇️  开始下载（1080p）...", file=output_stream, flush=True)
        download_opts = {
            "format": (
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[height<=1080]+bestaudio"
                "/best[height<=1080]/best"
            ),
            "merge_output_format": "mp4",
            "outtmpl": str(output_path),
            "noplaylist": True,
            "quiet": True,          # 关闭 yt-dlp 自带输出，改由 progress_hook 驱动
            "no_warnings": False,
            "progress_hooks": [progress_hook],
        }
        with yt_dlp.YoutubeDL(download_opts) as ydl:
            ydl.download([url])

        # 确保最后一个进度条已关闭（异常路径保险）
        if _state["pbar"] is not None:
            _state["pbar"].close()

        print(f"✅ 下载完成: {output_path}", file=output_stream)

        return LocalFileInfo(
            file_path=output_path,
            platform=platform,
            video_id=video_id,
            title=info.get("title", ""),
            duration=duration,
            uploader=uploader,
            upload_date=upload_date,
            metadata=info,
        )
    
    def _download_with_bbdown(self, url: str, force_redownload: bool) -> LocalFileInfo:
        """
        使用 BBDown 下载B站视频（降级方案）
        
        注意：需要先安装 BBDown
        安装方式：https://github.com/nilaoda/BBDown
        
        Args:
            url: B站视频URL
            force_redownload: 是否强制重新下载
            
        Returns:
            LocalFileInfo: 下载后的文件信息
        """
        if not self.bbdown_path:
            raise Exception("BBDown 未安装，请执行: brew install bbdown")
        
        # 提取B站视频ID
        bv_match = re.search(r'BV[\w]+', url)
        av_match = re.search(r'av(\d+)', url)
        
        if bv_match:
            video_id = bv_match.group(0)
        elif av_match:
            video_id = f"av{av_match.group(1)}"
        else:
            video_id = "unknown"
        
        # BBDown 默认输出文件名格式
        # 这里简化处理，假设输出为 视频标题.mp4
        temp_dir = self.download_dir / "temp_bbdown"
        temp_dir.mkdir(exist_ok=True)
        
        # 执行 BBDown（限制1080p）
        cmd = [
            self.bbdown_path, 
            url, 
            "--work-dir", str(temp_dir),
            "-q", "1080P 高码率",  # 限制画质为1080P
            "--download-danmaku", "false"  # 不下载弹幕
        ]
        
        # 使用 Popen 获取输出并在需要时提取进度信息
        output_stream = sys.stderr if self.json_mode else sys.stdout
        print("🚀 启动 BBDown 下载...", file=output_stream, flush=True)

        # 确保 JSON 模式下，子进程的 stdout/stderr 也重定向到 stderr (或 None)
        # 否则会污染主进程的 JSON 输出管道
        stdout_target = sys.stderr if self.json_mode else None
        
        # 注意: 如果需要捕获输出做分析，可以用 subprocess.PIPE，这里简单重定向
        subprocess.run(cmd, check=True, stdout=stdout_target, stderr=stdout_target)
        
        # 查找下载的文件（BBDown会自动命名）
        downloaded_files = list(temp_dir.glob("*.mp4"))
        if not downloaded_files:
            raise Exception("BBDown 下载完成但未找到输出文件")
        
        # 重命名并移动文件
        src_file = downloaded_files[0]
        title = self._sanitize_filename(src_file.stem)
        filename = f"{title}_bilibili_{video_id}.mp4"
        output_path = self.download_dir / filename
        
        src_file.rename(output_path)
        
        output_stream = sys.stderr if self.json_mode else sys.stdout
        print(f"✅ BBDown 下载完成: {output_path}", file=output_stream, flush=True)
        
        return LocalFileInfo(
            file_path=output_path,
            platform="bilibili",
            video_id=video_id,
            title=title,
            duration=None,
            uploader=None,
            upload_date=None,
            metadata={}
        )
    
    def _download_with_xhs(self, url: str, force_redownload: bool) -> LocalFileInfo:
        """
        使用 XHS-Downloader 下载小红书视频（降级方案）
        
        注意：需要先克隆 XHS-Downloader 到项目目录
        
        Args:
            url: 小红书URL
            force_redownload: 是否强制重新下载
            
        Returns:
            LocalFileInfo: 下载后的文件信息
        """
        import sys
        import asyncio
        from pathlib import Path
        
        # 检查 Python 版本
        python_version = sys.version_info
        if python_version < (3, 12):
            raise NotImplementedError(
                f"XHS-Downloader 需要 Python 3.12+，但当前版本是 {python_version.major}.{python_version.minor}\n"
                "\n"
                "解决方案：\n"
                "1. 手动下载小红书视频：\n"
                "   - 访问视频页面\n"
                "   - 使用浏览器插件或在线工具下载\n"
                "   - 将视频保存到 videos/ 目录\n"
                "   - 然后运行：make run VIDEO=videos/你的视频.mp4\n"
                "\n"
                "2. 升级 Python 到 3.12+\n"
                "3. 使用在线小红书下载工具（推荐）\n"
            )
        
        # 检查 XHS-Downloader 是否存在
        xhs_path = Path(__file__).parent.parent / "XHS-Downloader"
        if not xhs_path.exists():
            raise NotImplementedError(
                "XHS-Downloader 未找到。\n"
                f"请确保该文件夹存在于: {xhs_path}"
            )
        
        # 添加到 sys.path
        if str(xhs_path) not in sys.path:
            sys.path.insert(0, str(xhs_path))
        
        try:
            from source import XHS
        except ImportError as e:
            raise NotImplementedError(
                f"无法导入 XHS-Downloader: {e}\n"
                "请确保已安装所有依赖：\n"
                "pip install -r XHS-Downloader/requirements.txt"
            )
        
        # 运行异步下载
        return asyncio.run(self._async_download_xhs(url, XHS))
    
    async def _async_download_xhs(self, url: str, XHS) -> LocalFileInfo:
        """异步下载小红书视频"""
        import shutil
        
        # 配置 XHS-Downloader
        work_path = str(self.download_dir.parent / "temp_xhs")
        folder_name = "download"
        
        async with XHS(
            work_path=work_path,
            folder_name=folder_name,
            image_download=False,  # 只下载视频
            video_download=True,
            cookie="",
        ) as xhs:
            # 下载作品
            result = await xhs.extract(url, download=True)
            
            if not result:
                raise Exception("无法获取小红书视频信息")
            
            # 查找下载的文件
            download_dir = Path(work_path) / folder_name
            video_files = list(download_dir.rglob("*.mp4"))
            
            if not video_files:
                raise Exception("视频下载失败，未找到 MP4 文件")
            
            # 获取文件
            src_file = video_files[0]
            
            # 重命名并移动
            video_id = result.get("作品ID", "unknown")
            title = self._sanitize_filename(result.get("作品标题", "untitled"))
            filename = f"xiaohongshu_{video_id}_{title}.mp4"
            dest_file = self.download_dir / filename
            
            # 移动文件
            shutil.move(str(src_file), str(dest_file))
            
            # 清理临时目录
            if Path(work_path).exists():
                shutil.rmtree(work_path)
            
            # 返回信息
            return LocalFileInfo(
                file_path=dest_file,
                platform="xiaohongshu",
                video_id=video_id,
                title=result.get("作品标题", ""),
                duration=None,
                uploader=result.get("作者昵称", ""),
                upload_date=result.get("发布时间", ""),
                metadata=result
            )


def extract_url_from_text(text: str) -> Optional[str]:
    """
    从文本中提取视频URL（支持从分享文本中自动提取）
    
    支持的场景：
    - 纯URL输入
    - URL + 其他文本（自动提取URL）
    - 多个URL（返回第一个有效的）
    
    Args:
        text: 输入文本（可能包含URL和其他内容）
        
    Returns:
        提取到的URL，或None
    """
    text = text.strip()

    # ── B站特殊处理：从文本中提取 BV ID 并规范化 URL ──────────────────────────
    # BV ID 固定为 12 字符（BV + 10位字母数字），直接用正则提取，
    # 防止 "BV1JHPgzXEHNvd_source=..." 这类缺 ? 分隔符的粘贴错误。
    bv_match = re.search(r'(BV[a-zA-Z0-9]{10})', text)
    if bv_match and 'bilibili' in text.lower():
        bv_id = bv_match.group(1)
        return f'https://www.bilibili.com/video/{bv_id}'

    # ── 通用短链展开：b23.tv ──────────────────────────────────────────────────
    b23_match = re.search(r'(https?://b23\.tv/[^\s?&]+)', text)
    if b23_match:
        url = b23_match.group(1)
        url = re.sub(r'[.,;:\'"\)\]]+$', '', url)
        return url

    # 支持的视频平台域名模式
    video_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[^&\s]+',
        r'https?://(?:www\.)?youtu\.be/[^\s?&]+',
        r'https?://(?:www\.)?bilibili\.com/video/[^\s?&]+',
        r'https?://(?:www\.)?xiaohongshu\.com/[^\s?&]+',
        r'https?://xhslink\.com/[^\s?&]+',
        r'https?://(?:www\.)?douyin\.com/[^\s?&]+',
        r'https?://(?:www\.)?tiktok\.com/[^\s?&]+',
        r'https?://(?:www\.)?twitter\.com/[^\s?&]+',
        r'https?://(?:www\.)?x\.com/[^\s?&]+',
        # 通用URL模式（作为后备）
        r'https?://[^\s]+',
    ]
    
    # 逐个尝试每个模式
    for pattern in video_patterns:
        matches = re.findall(pattern, text)
        if matches:
            url = matches[0]
            # 移除末尾的特殊字符（比如句号、引号等）
            url = re.sub(r'[.,;:\'"\)\]]+$', '', url)
            return url
    
    return None


def main():
    """命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="统一视频下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法：
  python video_downloader.py https://www.youtube.com/watch?v=xxxxx
  python video_downloader.py https://www.bilibili.com/video/BVxxxxxx
  python video_downloader.py -d my_videos https://example.com/video
  python video_downloader.py --json https://www.youtube.com/watch?v=xxxxx
  
自动URL提取（支持复制分享文本）：
  python video_downloader.py "分享一个视频：https://www.bilibili.com/video/BVxxxxx 看看"
  python video_downloader.py "youtube.com/watch?v=xxxxx"
        """
    )
    
    parser.add_argument("url", help="视频URL或包含URL的文本（支持自动提取）")
    parser.add_argument(
        "-d", "--dir",
        default="videos",
        help="下载目录，默认为 videos/"
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="强制重新下载（即使文件已存在）"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出JSON格式（用于脚本集成）"
    )
    
    args = parser.parse_args()
    
    # 🩹 补丁：手动检查 --json 参数（防止 argparse 在特定参数顺序下解析失败）
    if "--json" in sys.argv:
        args.json = True
    
    # 从输入中提取URL（支持自动提取）
    url = extract_url_from_text(args.url)
    if not url:
        print(f"❌ 错误：无法从输入中提取有效的视频URL")
        print(f"输入内容：{args.url}")
        print("\n支持的URL格式：")
        print("  • YouTube: youtube.com/watch?v=... 或 youtu.be/...")
        print("  • Bilibili: bilibili.com/video/BV... 或 b23.tv/...")
        print("  • 小红书: xiaohongshu.com/... 或 xhslink.com/...")
        print("  • 抖音: douyin.com/...")
        print("  • Twitter/X: twitter.com/... 或 x.com/...")
        exit(1)
    
    # 创建下载器并下载
    downloader = VideoDownloader(download_dir=args.dir, json_mode=args.json)
    
    try:
        file_info = downloader.download_video(url, force_redownload=args.force)
        
        if args.json:
            # JSON 输出（用于脚本集成）
            output = {
                "file_path": str(file_info.file_path),
                "platform": file_info.platform,
                "video_id": file_info.video_id,
                "title": file_info.title,
                "duration": file_info.duration,
                "uploader": file_info.uploader,
                "upload_date": file_info.upload_date,
            }
            # 直接输出到 stdout，不带其他信息
            # (Remove import sys here because it's shadowing global sys and causing UnboundLocalError earlier)
            sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        else:
            # 友好的文本输出
            print("\n" + "="*50)
            print("📊 下载信息")
            print("="*50)
            print(f"文件路径: {file_info.file_path}")
            print(f"平台:     {file_info.platform}")
            print(f"视频ID:   {file_info.video_id}")
            print(f"标题:     {file_info.title}")
            if file_info.duration:
                print(f"时长:     {file_info.duration:.1f} 秒")
            if file_info.uploader:
                print(f"上传者:   {file_info.uploader}")
            if file_info.upload_date:
                print(f"上传日期: {file_info.upload_date}")
            print("="*50)
            # 也输出 JSON 作为最后一行，便于 Makefile 提取
            output = {
                "file_path": str(file_info.file_path),
                "platform": file_info.platform,
                "video_id": file_info.video_id,
                "title": file_info.title,
                "duration": file_info.duration,
                "uploader": file_info.uploader,
                "upload_date": file_info.upload_date,
            }
            print(json.dumps(output, ensure_ascii=False))
        
        # 如果需要自动处理
        if hasattr(args, 'process') and args.process:
            print(f"\n📹 开始处理视频...")
            from core.process_video import process_video
            process_video(
                video_path=file_info.file_path,
                output_dir=Path("output"),
                with_frames=getattr(args, 'ocr', False),
                ocr_lang="ch",
                ocr_engine="vision",
                source_url=url,
                platform_title=file_info.title,
                cover_image_path=file_info.screenshot_path,
                video_info=file_info.metadata,
            )
        
    except Exception as e:
        if  "--json" in sys.argv:
            print(f"❌ 下载失败: {e}", file=sys.stderr)
        else:
            print(f"\n❌ 下载失败: {e}")
        exit(1)


def download_cli(args):
    """统一CLI适配函数"""
    # 从输入中提取URL
    url = extract_url_from_text(args.url)
    if not url:
        print(f"❌ 错误：无法从输入中提取有效的视频URL: {args.url}")
        exit(1)
    
    # 创建下载器并下载
    output_dir = args.output if hasattr(args, 'output') and args.output else "videos"
    downloader = VideoDownloader(download_dir=output_dir)
    
    try:
        file_info = downloader.download_video(url, force_redownload=getattr(args, 'force', False))
        
        print("\n" + "="*50)
        print("✅ 下载完成")
        print("="*50)
        print(f"文件路径: {file_info.file_path}")
        print(f"平台:     {file_info.platform}")
        print(f"标题:     {file_info.title}")
        if file_info.duration:
            print(f"时长:     {file_info.duration:.1f} 秒")
        print("="*50)
        
        # 如果需要自动处理
        if args.process:
            print(f"\n📹 开始处理视频...")
            from core.process_video import process_video
            process_video(
                video_path=file_info.file_path,
                output_dir=Path("output"),
                with_frames=args.ocr,
                ocr_lang="ch",
                ocr_engine="vision",
                source_url=url,
                platform_title=file_info.title,
            )
        
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        exit(1)


if __name__ == "__main__":
    main()
