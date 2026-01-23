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
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

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


class VideoDownloader:
    """统一视频下载器"""
    
    def __init__(self, download_dir: str = "videos"):
        """
        初始化下载器
        
        Args:
            download_dir: 视频下载目录，默认为 videos/
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
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
            print(f"⚠️  检查数据库时出错: {e}")
            return None
    
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
        print(f"📥 准备下载视频: {url}")
        
        # 检测平台
        platform = self._detect_platform(url)
        print(f"🔍 检测到平台: {platform}")
        
        # 检查数据库中是否已存在
        if not force_redownload:
            existing = self.check_already_downloaded(url)
            if existing:
                print(f"✅ 视频已在数据库中 (ID: {existing['video_id']})")
                print(f"   标题: {existing['title']}")
                print(f"   文件: {existing['file_path']}")
                print(f"💡 如需重新下载，请使用 force_redownload=True")
                
                # 检查文件是否仍然存在
                if existing['file_path'] and Path(existing['file_path']).exists():
                    # 返回已存在的文件信息
                    return LocalFileInfo(
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
                    print(f"⚠️  原文件已不存在，将重新下载")
        
        # 尝试下载
        try:
            # 1. 首选方案：yt-dlp（支持大多数平台）
            return self._download_with_ytdlp(url, platform, force_redownload)
        except Exception as e:
            print(f"⚠️  yt-dlp 下载失败: {e}")
            
            # 2. B站降级方案：BBDown
            if platform == "bilibili":
                try:
                    print("🔄 尝试使用 BBDown 下载...")
                    return self._download_with_bbdown(url, force_redownload)
                except Exception as e2:
                    print(f"❌ BBDown 下载失败: {e2}")
                    raise Exception(f"B站视频下载失败（已尝试 yt-dlp 和 BBDown）")
            
            # 3. 小红书降级方案：XHS-Downloader
            elif platform == "xiaohongshu":
                try:
                    print("🔄 尝试使用 XHS-Downloader 下载...")
                    return self._download_with_xhs(url, force_redownload)
                except Exception as e2:
                    print(f"❌ XHS-Downloader 下载失败: {e2}")
                    raise Exception(f"小红书视频下载失败（已尝试 yt-dlp 和 XHS-Downloader）")
            
            # 其他平台直接抛出异常
            raise Exception(f"{platform} 平台视频下载失败: {e}")
    
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
        
        pbar = None
        if total_size:
            # 进度条输出到 stderr，这样即使 stdout 被重定向也能看到
            pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc='下载进度', file=sys.stderr)
        
        # 用于解析 yt-dlp 的进度输出
        last_downloaded = 0
        
        for line in process.stdout:
            # yt-dlp 进度格式: [download]  45.8% of 123.45MiB at 1.23MiB/s ETA 00:23
            if '[download]' in line and '%' in line:
                # 尝试提取百分比
                match = re.search(r'(\d+\.\d+)%', line)
                if match and pbar:
                    percent = float(match.group(1))
                    downloaded = int(total_size * percent / 100)
                    if downloaded > last_downloaded:
                        pbar.update(downloaded - last_downloaded)
                        last_downloaded = downloaded
                elif not pbar:
                    # 如果没有总大小，至少显示进度信息到 stderr
                    print(line.strip(), file=sys.stderr)
            elif '[download] Destination:' in line or '[download] ' in line:
                # 显示其他重要信息到 stderr
                if not pbar:
                    print(line.strip(), file=sys.stderr)
        
        if pbar:
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
        # 移除非法字符
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 替换空格和特殊字符
        filename = re.sub(r'[\s]+', '_', filename)
        # 移除前后的点和空格
        filename = filename.strip('. ')
        # 截断过长的文件名
        if len(filename) > max_length:
            filename = filename[:max_length]
        return filename or "video"
    
    def _download_with_ytdlp(self, url: str, platform: str, force_redownload: bool) -> LocalFileInfo:
        """
        使用 yt-dlp 下载视频
        
        Args:
            url: 视频URL
            platform: 平台名称
            force_redownload: 是否强制重新下载
            
        Returns:
            LocalFileInfo: 下载后的文件信息
        """
        if not self.ytdlp_path:
            raise Exception("yt-dlp 未安装或未找到在 PATH 中")
        
        # 先获取视频信息（不下载）
        print("📋 获取视频信息...")
        info_cmd = [self.ytdlp_path, "--dump-json", "--no-playlist", url]
        result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # 提取元数据
        video_id = info.get("id", "unknown")
        title = self._sanitize_filename(info.get("title", "video"))
        duration = info.get("duration")
        uploader = info.get("uploader")
        upload_date = info.get("upload_date")
        filesize = info.get("filesize") or info.get("filesize_approx")
        
        # 显示视频信息
        if filesize:
            filesize_mb = filesize / (1024 * 1024)
            print(f"📦 文件大小: {filesize_mb:.1f} MB")
        
        # 构造文件名：标题_平台_视频ID.mp4
        filename = f"{title}_{platform}_{video_id}.mp4"
        output_path = self.download_dir / filename
        
        # 检查文件是否已存在
        if output_path.exists() and not force_redownload:
            print(f"✅ 文件已存在，跳过下载: {output_path}")
            return LocalFileInfo(
                file_path=output_path,
                platform=platform,
                video_id=video_id,
                title=info.get("title", ""),
                duration=duration,
                uploader=uploader,
                upload_date=upload_date,
                metadata=info
            )
        
        # 下载视频（限制1080p，节省空间和带宽）
        print(f"⬇️  开始下载（1080p）...")
        download_cmd = [
            self.ytdlp_path,
            "--no-playlist",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "-o", str(output_path),
        ]
        
        # 添加进度条支持
        if TQDM_AVAILABLE:
            download_cmd.extend(["--newline", "--progress"])
        
        download_cmd.append(url)
        
        # 使用 Popen 实时捕获输出并显示进度
        if TQDM_AVAILABLE:
            self._download_with_progress(download_cmd, filesize)
        else:
            subprocess.run(download_cmd, check=True)
        
        print(f"✅ 下载完成: {output_path}")
        
        return LocalFileInfo(
            file_path=output_path,
            platform=platform,
            video_id=video_id,
            title=info.get("title", ""),
            duration=duration,
            uploader=uploader,
            upload_date=upload_date,
            metadata=info
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
        temp_dir = self.download_dir / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        # 执行 BBDown（限制1080p）
        cmd = [
            self.bbdown_path, 
            url, 
            "--work-dir", str(temp_dir),
            "-q", "1080P 高码率",  # 限制画质为1080P
            "--download-danmaku", "false"  # 不下载弹幕
        ]
        subprocess.run(cmd, check=True)
        
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
        
        print(f"✅ BBDown 下载完成: {output_path}")
        
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
                "XHS-Downloader 未安装。\n"
                f"请先克隆: git clone https://github.com/JoeanAmier/XHS-Downloader.git"
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
    
    # 支持的视频平台域名模式
    video_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[^&\s]+',
        r'https?://(?:www\.)?youtu\.be/[^\s?&]+',
        r'https?://(?:www\.)?bilibili\.com/video/[^\s?&]+',
        r'https?://b23\.tv/[^\s?&]+',
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
    downloader = VideoDownloader(download_dir=args.dir)
    
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
            import sys
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
            )
        
    except Exception as e:
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
