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
    tags: List[str] = []
    created_at: datetime
    type: str

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

# #region 错误响应

class ErrorResponse(BaseModel):
    """错误响应"""
    status: int
    detail: str
    timestamp: datetime = Field(default_factory=datetime.now)

# #endregion

# #endregion
