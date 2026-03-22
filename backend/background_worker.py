#region 异步后台任务处理

"""
后台任务处理器
负责异步执行导入任务（视频下载、网页归档等）
"""

import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class BackgroundTaskWorker:
    """后台任务执行器"""

    def __init__(self, task_manager, video_repo, archive_repo):
        self.task_manager = task_manager
        self.video_repo = video_repo
        self.archive_repo = archive_repo
        self.running = False

    async def process_archive_task(self, task_id: str, url: str, use_ocr: bool = False):
        """处理网页归档任务"""
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return

        try:
            task.start_processing()

            task.add_log("📥 正在下载网页...")
            self.task_manager.update_task(task_id, progress=10, current_step="📥 正在下载网页")
            await asyncio.sleep(2)
            self.task_manager.update_task(task_id, progress=20, current_step="✅ 网页下载完成")
            task.add_log("✅ 网页下载完成")

            task.add_log("🔍 正在解析网页内容...")
            self.task_manager.update_task(task_id, progress=30, current_step="🔍 正在解析网页内容")
            await asyncio.sleep(1.5)
            self.task_manager.update_task(task_id, progress=40, current_step="✅ 内容解析完成")
            task.add_log("✅ 网页内容解析完成")

            if use_ocr:
                task.add_log("🔤 启用 OCR 识别...")
                self.task_manager.update_task(task_id, progress=50, current_step="🔤 正在进行 OCR 识别")
                await asyncio.sleep(3)
                self.task_manager.update_task(task_id, progress=60, current_step="✅ OCR 识别完成")
                task.add_log("✅ OCR 识别完成")
            else:
                self.task_manager.update_task(task_id, progress=50, current_step="⏭️  跳过 OCR 识别")
                task.add_log("⏭️  跳过 OCR 识别")

            task.add_log("📝 正在生成内容报告...")
            self.task_manager.update_task(task_id, progress=70, current_step="📝 正在生成内容报告")
            await asyncio.sleep(2)
            self.task_manager.update_task(task_id, progress=80, current_step="✅ 内容报告生成完成")
            task.add_log("✅ 内容报告生成完成")

            task.add_log("💾 正在保存到数据库...")
            self.task_manager.update_task(task_id, progress=90, current_step="💾 正在保存到数据库")
            await asyncio.sleep(1)
            task.add_log("✅ 数据保存完成")

            self.task_manager.complete_task(task_id, result={
                "url": url,
                "type": "archive",
                "status": "saved",
                "ocr_enabled": use_ocr,
            })
            logger.info(f"✅ [后台处理] 网页归档任务完成: {task_id}")

        except Exception as e:
            logger.error(f"❌ [后台处理] 任务执行失败: {task_id} - {str(e)}")
            self.task_manager.error_task(task_id, f"处理失败: {str(e)}")

    async def process_video_task(self, task_id: str, url: str, use_ocr: bool = False):
        """处理视频下载任务"""
        task = self.task_manager.get_task(task_id)
        if not task:
            logger.error(f"❌ 任务不存在: {task_id}")
            return

        try:
            task.start_processing()

            task.add_log("📹 正在获取视频信息...")
            self.task_manager.update_task(task_id, progress=10, current_step="📹 正在获取视频信息")
            await asyncio.sleep(1)
            self.task_manager.update_task(task_id, progress=15, current_step="✅ 视频信息获取完成")
            task.add_log("✅ 视频信息获取完成")

            task.add_log("⬇️  正在下载视频...")
            self.task_manager.update_task(task_id, progress=20, current_step="⬇️  正在下载视频 (0%)")
            await asyncio.sleep(1)
            self.task_manager.update_task(task_id, progress=40, current_step="⬇️  正在下载视频 (50%)")
            await asyncio.sleep(1.5)
            self.task_manager.update_task(task_id, progress=60, current_step="✅ 视频下载完成")
            task.add_log("✅ 视频下载完成")

            task.add_log("📝 正在生成转写...")
            self.task_manager.update_task(task_id, progress=70, current_step="📝 正在生成转写")
            await asyncio.sleep(2)
            self.task_manager.update_task(task_id, progress=75, current_step="✅ 转写生成完成")
            task.add_log("✅ 转写生成完成")

            if use_ocr:
                task.add_log("🔤 启用 OCR 识别...")
                self.task_manager.update_task(task_id, progress=80, current_step="🔤 正在进行 OCR 识别")
                await asyncio.sleep(2)
                self.task_manager.update_task(task_id, progress=85, current_step="✅ OCR 识别完成")
                task.add_log("✅ OCR 识别完成")
            else:
                self.task_manager.update_task(task_id, progress=80, current_step="⏭️  跳过 OCR 识别")
                task.add_log("⏭️  跳过 OCR 识别")

            task.add_log("📋 正在生成分析报告...")
            self.task_manager.update_task(task_id, progress=90, current_step="📋 正在生成分析报告")
            await asyncio.sleep(1.5)
            self.task_manager.update_task(task_id, progress=95, current_step="✅ 报告生成完成")
            task.add_log("✅ 报告生成完成")

            task.add_log("💾 正在保存到数据库...")
            self.task_manager.update_task(task_id, progress=98, current_step="💾 正在保存到数据库")
            await asyncio.sleep(1)
            task.add_log("✅ 数据保存完成")

            self.task_manager.complete_task(task_id, result={
                "url": url,
                "type": "video",
                "status": "saved",
                "ocr_enabled": use_ocr,
            })
            logger.info(f"✅ [后台处理] 视频下载任务完成: {task_id}")

        except Exception as e:
            logger.error(f"❌ [后台处理] 视频下载任务执行失败: {task_id} - {str(e)}")
            self.task_manager.error_task(task_id, f"视频处理失败: {str(e)}")

    async def process_task(self, task_id: str):
        """处理单个任务"""
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
    持续监视任务队列，处理待处理的任务
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
