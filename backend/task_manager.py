#region 任务队列管理系统

"""
后端异步任务队列与状态追踪

目的：
  1. 管理后台任务的生命周期（pending -> processing -> completed/error）
  2. 提供任务状态查询接口
  3. 支持日志追踪与进度更新
"""

import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待处理
    PROCESSING = "processing"    # 正在处理
    COMPLETED = "completed"      # 完成
    ERROR = "error"              # 错误
    CANCELLED = "cancelled"      # 已取消


@dataclass
class TaskLog:
    """任务日志条目"""
    timestamp: str
    level: str  # info, warning, error
    message: str


@dataclass
class Task:
    """任务对象"""
    task_id: str
    task_type: str              # 'archive', 'video' 等
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    # 业务相关字段
    url: str = ""
    use_ocr: bool = False
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    # 进度追踪
    progress: int = 0           # 0-100%
    current_step: str = "初始化"  # 当前处理步骤

    # 日志
    logs: list = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 序列化）"""
        data = asdict(self)
        data["status"] = self.status.value
        data["logs"] = self.logs[-20:] if self.logs else []
        data["error"] = self.error_message
        return data

    def add_log(self, message: str, level: str = "info"):
        """添加日志"""
        log = TaskLog(
            timestamp=datetime.now().isoformat(),
            level=level,
            message=message
        )
        self.logs.append(asdict(log))

        if level == "error":
            logger.error(f"[Task {self.task_id}] {message}")
        elif level == "warning":
            logger.warning(f"[Task {self.task_id}] {message}")
        else:
            logger.info(f"[Task {self.task_id}] {message}")

    def start_processing(self):
        """标记任务开始处理"""
        self.status = TaskStatus.PROCESSING
        self.started_at = datetime.now().isoformat()
        self.add_log(f"🔄 开始处理: {self.task_type} ({self.url})")


class TaskManager:
    """任务管理器 - 中央队列与状态存储"""

    def __init__(self, max_tasks: int = 1000):
        self.tasks: Dict[str, Task] = {}
        self.max_tasks = max_tasks

    def create_task(self, task_type: str, url: str, use_ocr: bool = False) -> str:
        """创建并注册一个新任务"""
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            task_id=task_id,
            task_type=task_type,
            url=url,
            use_ocr=use_ocr
        )

        self.tasks[task_id] = task
        logger.info(f"✨ [任务管理] 创建新任务: {task_id} ({task_type})")

        if len(self.tasks) > self.max_tasks:
            self._cleanup_old_tasks()

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务对象"""
        return self.tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        current_step: Optional[str] = None,
        result: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        """更新任务状态"""
        task = self.get_task(task_id)
        if not task:
            logger.warning(f"❌ 任务不存在: {task_id}")
            return

        if status:
            task.status = status
        if progress is not None:
            task.progress = min(100, max(0, progress))
        if current_step:
            task.current_step = current_step
        if result is not None:
            task.result = result
        if error_message:
            task.error_message = error_message
            task.status = TaskStatus.ERROR
            task.completed_at = datetime.now().isoformat()
            task.add_log(f"❌ 错误: {error_message}", level="error")

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now().isoformat()
            task.progress = 100
            task.add_log("✅ 任务完成")
        elif status == TaskStatus.ERROR:
            task.completed_at = datetime.now().isoformat()

    def complete_task(self, task_id: str, result: Dict[str, Any] = None):
        """标记任务完成"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.progress = 100
            if result is not None:
                task.result = result
            task.add_log("✅ 任务完成")
            logger.info(f"✅ [任务管理] 任务完成: {task_id}")

    def error_task(self, task_id: str, error_message: str):
        """标记任务出错"""
        task = self.get_task(task_id)
        if task:
            task.status = TaskStatus.ERROR
            task.completed_at = datetime.now().isoformat()
            task.error_message = error_message
            task.add_log(f"❌ 错误: {error_message}", level="error")
            logger.error(f"❌ [任务管理] 任务出错: {task_id} - {error_message}")

    def _cleanup_old_tasks(self):
        """清理过期任务（保留最新任务）"""
        sorted_tasks = sorted(
            self.tasks.items(),
            key=lambda item: item[1].created_at,
            reverse=True
        )
        for task_id, _ in sorted_tasks[self.max_tasks:]:
            del self.tasks[task_id]
        logger.info(f"🧹 [任务管理] 清理过期任务，当前任务数: {len(self.tasks)}")

    def get_statistics(self) -> dict:
        """获取任务统计"""
        return {
            "total": len(self.tasks),
            "pending": sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING),
            "processing": sum(1 for task in self.tasks.values() if task.status == TaskStatus.PROCESSING),
            "completed": sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED),
            "error": sum(1 for task in self.tasks.values() if task.status == TaskStatus.ERROR),
        }

    def get_stats(self) -> dict:
        """兼容旧接口名。"""
        return self.get_statistics()


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


task_manager = get_task_manager()

#endregion
