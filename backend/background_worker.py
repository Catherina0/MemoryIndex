#region 异步后台任务处理

"""
后台任务处理器
负责异步执行导入任务（视频下载、网页归档等）
"""

import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#region 后台任务处理器类

class BackgroundTaskWorker:
    """后台任务执行器"""

    def __init__(self, task_manager, video_repo, archive_repo):
        self.task_manager = task_manager
        self.video_repo = video_repo
        self.archive_repo = archive_repo
        self.running = False

    async def process_archive_task(self, task_id: str, url: str, use_ocr: bool = False):
        """处理网页归档任务（真实实现）"""
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return

        try:
            task.start_processing()
            task.add_log(f"🌐 开始归档: {url}")
            self.task_manager.update_task(task_id, progress=5, current_step="🌐 初始化归档任务")

            # 导入真实归档入口（延迟导入，避免启动时拖慢）
            from core.archive_processor import archive_and_save

            self.task_manager.update_task(task_id, progress=10, current_step="📥 正在下载并解析网页...")
            task.add_log("📥 正在下载网页内容...")

            # archive_and_save 是 async def，直接 await
            # 内部包含: 爬取 → LLM分析(3次) → DB存储 → 文件夹重命名
            db_id = await archive_and_save(
                url=url,
                output_dir="output",
                with_ocr=use_ocr,
                headless=True
            )

            self.task_manager.update_task(task_id, progress=98, current_step="✅ 归档完成，已入库")
            task.add_log(f"✅ 网页归档完成 (数据库 ID: {db_id})")

            self.task_manager.complete_task(task_id, result={
                "url": url,
                "type": "archive",
                "status": "saved",
                "db_id": db_id,
                "ocr_enabled": use_ocr,
            })
            logger.info(f"✅ [后台处理] 网页归档任务完成: {task_id} (DB ID: {db_id})")

        except Exception as e:
            logger.error(f"❌ [后台处理] 归档任务失败: {task_id} - {str(e)}")
            task.add_log(f"❌ 归档失败: {str(e)}")
            self.task_manager.error_task(task_id, f"归档失败: {str(e)}")

    async def process_video_task(self, task_id: str, url: str, use_ocr: bool = False):
        """处理视频下载任务（真实实现）"""
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return

        try:
            task.start_processing()
            task.add_log(f"📹 开始处理视频: {url}")
            self.task_manager.update_task(task_id, progress=5, current_step="📹 初始化视频任务")

            # 延迟导入，避免启动时加载
            from core.video_downloader import VideoDownloader
            from core.process_video import process_video

            # ── Step 1: 下载视频 ──────────────────────────
            self.task_manager.update_task(task_id, progress=10, current_step="⬇️  正在下载视频...")
            task.add_log("⬇️  开始下载视频...")

            loop = asyncio.get_running_loop()

            def _download():
                downloader = VideoDownloader(download_dir="videos")
                return downloader.download_video(url)

            local_info = await loop.run_in_executor(None, _download)

            self.task_manager.update_task(task_id, progress=40, current_step="✅ 视频下载完成")
            task.add_log(f"✅ 视频下载完成: {local_info.title}")

            # ── Step 2: 处理视频（转写/OCR/LLM报告/入库） ──
            self.task_manager.update_task(task_id, progress=45, current_step="🎬 正在处理视频（转写 + AI分析）...")
            task.add_log("🎬 开始转写与 AI 分析...")

            video_path = Path(local_info.file_path)
            output_dir = Path("output")
            source_url = url

            def _process():
                process_video(
                    video_path=video_path,
                    output_dir=output_dir,
                    with_frames=use_ocr,
                    source_url=source_url,
                    platform_title=local_info.title,
                    smart_ocr=True,
                )

            await loop.run_in_executor(None, _process)

            self.task_manager.update_task(task_id, progress=98, current_step="✅ 视频处理完成，已入库")
            task.add_log("✅ 视频处理完成，已保存到数据库")

            self.task_manager.complete_task(task_id, result={
                "url": url,
                "type": "video",
                "status": "saved",
                "ocr_enabled": use_ocr,
                "title": local_info.title,
            })
            logger.info(f"✅ [后台处理] 视频任务完成: {task_id}")

        except Exception as e:
            logger.error(f"❌ [后台处理] 视频任务失败: {task_id} - {str(e)}")
            task.add_log(f"❌ 视频处理失败: {str(e)}")
            self.task_manager.error_task(task_id, f"视频处理失败: {str(e)}")

    async def process_task(self, task_id: str):
        """处理单个任务（根据类型分发）"""
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.warning(f"⚠️  任务不存在: {task_id}")
            return

        logger.info(f"🔄 [后台处理] 开始处理任务: {task_id} (类型: {task.task_type})")

        if task.task_type == "archive":
            await self.process_archive_task(task_id, task.url, task.use_ocr)
        elif task.task_type == "video":
            await self.process_video_task(task_id, task.url, task.use_ocr)
        else:
            logger.warning(f"⚠️  未知任务类型: {task.task_type}")
            self.task_manager.error_task(task_id, f"未知任务类型: {task.task_type}")

#endregion

#region 全局工作器管理

_background_worker: Optional["BackgroundTaskWorker"] = None
_background_worker_thread: Optional[threading.Thread] = None


def get_background_worker() -> BackgroundTaskWorker:
    """获取全局后台处理器实例"""
    global _background_worker
    if not _background_worker:
        from backend.task_manager import get_task_manager
        from db.repository import ArchiveRepository, VideoRepository

        _background_worker = BackgroundTaskWorker(
            get_task_manager(),
            VideoRepository(),
            ArchiveRepository(),
        )
    return _background_worker


async def start_background_worker_loop():
    """
    启动后台任务处理循环
    持续监视任务队列，处理 pending 状态的任务
    """
    worker = get_background_worker()
    worker.running = True

    logger.info("🚀 [后台处理] 后台任务处理循环已启动")

    while worker.running:
        try:
            from backend.task_manager import TaskStatus, get_task_manager

            task_manager = get_task_manager()
            pending_tasks = [
                (task_id, task)
                for task_id, task in task_manager.tasks.items()
                if task.status == TaskStatus.PENDING
            ]

            for task_id, _task in pending_tasks:
                logger.info(f"📦 [后台处理] 处理待处理任务: {task_id}")
                await worker.process_task(task_id)

            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"❌ [后台处理] 后台任务循环错误: {str(e)}")
            await asyncio.sleep(5)


def start_background_worker():
    """
    启动后台任务处理线程
    在应用启动时调用
    """
    global _background_worker_thread
    worker = get_background_worker()

    if worker.running and _background_worker_thread and _background_worker_thread.is_alive():
        logger.warning("⚠️  [后台处理] 后台任务处理线程已在运行")
        return

    def run_event_loop():
        """在新线程中运行事件循环"""
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_background_worker_loop())
        except Exception as e:
            logger.error(f"❌ [后台处理] 事件循环错误: {str(e)}")
        finally:
            worker.running = False
            if loop is not None:
                loop.close()

    _background_worker_thread = threading.Thread(target=run_event_loop, daemon=True)
    _background_worker_thread.start()
    logger.info("✅ [后台处理] 后台任务处理线程已启动")


def stop_background_worker():
    """停止后台任务处理线程。"""
    global _background_worker_thread

    worker = get_background_worker()
    if not worker.running:
        return

    worker.running = False
    if _background_worker_thread and _background_worker_thread.is_alive():
        _background_worker_thread.join(timeout=5)

    _background_worker_thread = None
    logger.info("🛑 [后台处理] 后台任务处理线程已停止")

#endregion

#endregion
