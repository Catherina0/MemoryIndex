#region Pydantic 数据模型定义

"""
FastAPI 请求/响应数据模型（Pydantic）
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# #region 搜索相关模型

class SearchResultItem(BaseModel):
    """搜索结果条目"""
    id: int
    type: str = Field(..., description="内容类型: video/archive")
    title: str
    summary: Optional[str] = None
    source_type: str
    tags: List[str] = []
    created_at: datetime
    url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "video",
                "title": "AI 视频标题",
                "summary": "视频摘要...",
                "source_type": "youtube",
                "tags": ["AI", "技术"],
                "created_at": "2025-03-18T00:00:00Z"
            }
        }

class SearchResultResponse(BaseModel):
    """搜索响应"""
    results: List[SearchResultItem]
    total: int
    limit: int
    offset: int
    estimated_time_ms: Optional[float] = None

# #endregion

# #region 内容相关模型

class ArtifactDetail(BaseModel):
    """产物详情"""
    type: str  # transcript, ocr, report
    content: str
    model_name: Optional[str] = None
    created_at: Optional[datetime] = None

class VideoDetailResponse(BaseModel):
    """视频/内容详情响应"""
    id: int
    type: str  # video/archive
    title: str
    summary: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    created_at: datetime
    tags: List[str] = []
    
    # 内容数据
    transcript: Optional[str] = None
    ocr_text: Optional[str] = None
    report: Optional[str] = None
    raw_archive: Optional[str] = None
    readme_text: Optional[str] = None
    artifacts: Optional[List[ArtifactDetail]] = None
    
    # 视频特有字段
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "type": "video",
                "title": "视频标题",
                "source_type": "youtube",
                "tags": ["AI", "学习"],
                "created_at": "2025-03-18T00:00:00Z"
            }
        }

class ContentItemBase(BaseModel):
    """内容列表项基础模型"""
    id: int
    title: str
    summary: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    type: str  # 'video' 或 'archive'
    duration: Optional[float] = None  # 视频时长（秒）
    file_size: Optional[int] = None  # 文件大小（字节）

class ContentListResponse(BaseModel):
    """内容列表响应"""
    items: List[ContentItemBase]
    total: int
    limit: int
    offset: int

# #endregion

# #region 标签相关模型

class TagResponse(BaseModel):
    """标签响应"""
    id: int
    name: str
    count: int
    category: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "AI",
                "count": 42,
                "category": "技术"
            }
        }

# #endregion

# #region 统计相关模型

class StatsResponse(BaseModel):
    """统计信息响应"""
    total_videos: int
    total_archives: int
    total_tags: int
    top_tags: List[TagResponse]
    average_video_duration: Optional[float] = None
    storage_used_gb: Optional[float] = None
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_videos": 100,
                "total_archives": 50,
                "total_tags": 25,
                "top_tags": [
                    {"id": 1, "name": "AI", "count": 20, "category": "技术"}
                ],
                "last_updated": "2025-03-18T00:00:00Z"
            }
        }

# #endregion

# #region 导入相关模型

class ImportRequest(BaseModel):
    """导入请求"""
    url: str = Field(..., description="要导入的 URL")
    content_type: str = Field(
        default='auto',
        description="内容类型: auto/video/archive"
    )
    use_ocr: bool = Field(
        default=False,
        description="是否启用 OCR"
    )

class ImportResponse(BaseModel):
    """导入响应"""
    status: str = Field(..., description="状态: queued/processing/completed/error")
    task_id: Optional[str] = Field(None, description="后端任务ID")
    content_id: Optional[int] = Field(None, description="新建内容的 ID")
    message: str = Field(..., description="状态消息")
    content_type: Optional[str] = Field(None, description="检测到的内容类型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "task_id": "abc12345",
                "content_id": None,
                "message": "✅ 已创建 video 处理任务 (ID: abc12345)",
                "content_type": "video"
            }
        }

class TaskLog(BaseModel):
    """任务日志"""
    timestamp: str
    level: str  # info, warning, error
    message: str

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    task_type: str
    status: str  # pending, processing, completed, error
    url: str
    use_ocr: bool
    progress: int  # 0-100
    current_step: str
    
    # 时间信息
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # 结果
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    logs: List[TaskLog] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "abc12345",
                "task_type": "archive",
                "status": "processing",
                "url": "https://x.com/...",
                "use_ocr": False,
                "progress": 45,
                "current_step": "正在下载网页",
                "created_at": "2025-03-19T10:00:00",
                "started_at": "2025-03-19T10:00:02",
                "logs": [
                    {"timestamp": "2025-03-19T10:00:00", "level": "info", "message": "🔄 开始处理"},
                    {"timestamp": "2025-03-19T10:00:02", "level": "info", "message": "下载中..."}
                ]
            }
        }

# #endregion

# #region 错误响应

class ErrorResponse(BaseModel):
    """错误响应"""
    status: int
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)

# #endregion

# #endregion
