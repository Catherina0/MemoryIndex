"""
数据模型定义（使用 dataclass）
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """视频来源类型（扩展支持网页归档）"""
    LOCAL = 'local'
    YOUTUBE = 'youtube'
    BILIBILI = 'bilibili'
    TWITTER = 'twitter'
    XIAOHONGSHU = 'xiaohongshu'
    DOUYIN = 'douyin'
    TIKTOK = 'tiktok'
    # 网页归档类型
    WEB_ARCHIVE = 'web_archive'
    ZHIHU = 'zhihu'
    REDDIT = 'reddit'
    UNKNOWN = 'unknown'


class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'


class ArtifactType(str, Enum):
    """产物类型"""
    TRANSCRIPT = 'transcript'
    OCR = 'ocr'
    REPORT = 'report'


@dataclass
class Video:
    """视频记录"""
    # 必填字段
    content_hash: str
    title: str
    source_type: SourceType
    file_path: str
    
    # 可选字段
    id: Optional[int] = None
    video_id: Optional[str] = None
    source_url: Optional[str] = None
    platform_title: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    processing_config: Optional[Dict[str, Any]] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    
    # 时间戳
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # 关联数据（不存储在数据库，由查询填充）
    tags: List[str] = field(default_factory=list)
    topics: List['Topic'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'content_hash': self.content_hash,
            'video_id': self.video_id,
            'title': self.title,
            'source_type': self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type,
            'source_url': self.source_url,
            'platform_title': self.platform_title,
            'duration_seconds': self.duration_seconds,
            'file_path': self.file_path,
            'file_size_bytes': self.file_size_bytes,
            'processing_config': self.processing_config,
            'status': self.status.value if isinstance(self.status, ProcessingStatus) else self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'tags': self.tags,
        }


@dataclass
class Artifact:
    """处理产物"""
    video_id: int
    artifact_type: ArtifactType
    content_text: str
    
    id: Optional[int] = None
    content_json: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    model_name: Optional[str] = None
    model_params: Optional[Dict[str, Any]] = None
    char_count: Optional[int] = None
    word_count: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'video_id': self.video_id,
            'artifact_type': self.artifact_type.value if isinstance(self.artifact_type, ArtifactType) else self.artifact_type,
            'content_text': self.content_text,
            'content_json': self.content_json,
            'file_path': self.file_path,
            'model_name': self.model_name,
            'model_params': self.model_params,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class Tag:
    """标签"""
    name: str
    
    id: Optional[int] = None
    category: Optional[str] = None
    count: int = 0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'count': self.count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class Topic:
    """主题/章节"""
    video_id: int
    title: str
    
    id: Optional[int] = None
    summary: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    keywords: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    sequence: int = 0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'video_id': self.video_id,
            'title': self.title,
            'summary': self.summary,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'keywords': self.keywords,
            'key_points': self.key_points,
            'sequence': self.sequence,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class TimelineEntry:
    """时间线条目"""
    video_id: int
    timestamp_seconds: float
    
    id: Optional[int] = None
    frame_number: Optional[int] = None
    transcript_text: Optional[str] = None
    ocr_text: Optional[str] = None
    frame_path: Optional[str] = None
    is_key_frame: bool = False
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'video_id': self.video_id,
            'timestamp_seconds': self.timestamp_seconds,
            'frame_number': self.frame_number,
            'transcript_text': self.transcript_text,
            'ocr_text': self.ocr_text,
            'frame_path': self.frame_path,
            'is_key_frame': self.is_key_frame,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class SearchResult:
    """搜索结果"""
    video_id: int
    video_title: str
    source_field: str  # 'report' | 'transcript' | 'ocr' | 'topic'
    
    # 匹配信息
    matched_snippet: str
    full_content: Optional[str] = None
    
    # 时间信息
    timestamp_seconds: Optional[float] = None
    timestamp_range: Optional[tuple[float, float]] = None  # (start, end)
    
    # 元信息
    tags: List[str] = field(default_factory=list)
    source_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_path: Optional[str] = None
    
    # 搜索相关
    rank: Optional[float] = None  # BM25 排名分数
    relevance_score: Optional[float] = None
    
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'video_id': self.video_id,
            'video_title': self.video_title,
            'source_field': self.source_field,
            'matched_snippet': self.matched_snippet,
            'full_content': self.full_content,
            'timestamp_seconds': self.timestamp_seconds,
            'timestamp_range': self.timestamp_range,
            'tags': self.tags,
            'source_type': self.source_type,
            'duration_seconds': self.duration_seconds,
            'file_path': self.file_path,
            'rank': self.rank,
            'relevance_score': self.relevance_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
