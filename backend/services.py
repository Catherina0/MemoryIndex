#region 业务服务层

"""
业务逻辑服务层
处理搜索、内容获取、统计等业务需求
"""

import logging
from typing import Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# #region 搜索服务

class SearchService:
    """搜索业务服务"""
    
    def __init__(self, search_repo, video_repo, archive_repo):
        self.search_repo = search_repo
        self.video_repo = video_repo
        self.archive_repo = archive_repo
    
    def search(self, query: str, tags: Optional[List[str]] = None, 
               source_type: Optional[str] = None, limit: int = 20, offset: int = 0):
        """
        执行全文搜索
        
        Args:
            query: 搜索关键词
            tags: 标签过滤列表
            source_type: 内容类型过滤
            limit: 返回数量
            offset: 分页偏移
        
        Returns:
            SearchResultResponse 对象
        """
        try:
            # 调用数据库搜索
            results, total = self.search_repo.search(
                query=query,
                tags=tags,
                source_type=source_type,
                limit=limit,
                offset=offset
            )
            
            # 格式化结果
            from backend.models import SearchResultResponse, SearchResultItem
            
            items = []
            for result in results:
                item = SearchResultItem(
                    id=result.get('id'),
                    type=result.get('type'),
                    title=result.get('title'),
                    summary=result.get('summary'),
                    source_type=result.get('source_type'),
                    tags=result.get('tags', []),
                    created_at=result.get('created_at'),
                    url=result.get('url')
                )
                items.append(item)
            
            return SearchResultResponse(
                results=items,
                total=total,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"搜索错误: {str(e)}")
            raise

# #endregion

# #region 内容服务

class ContentService:
    """内容获取业务服务"""
    
    def __init__(self, video_repo, archive_repo):
        self.video_repo = video_repo
        self.archive_repo = archive_repo
    
    def list_videos(self, limit: int, offset: int, sort: str = "recent"):
        """
        列出视频
        
        Args:
            limit: 数量限制
            offset: 分页偏移
            sort: 排序方式 (recent/oldest/popular)
        
        Returns:
            ContentListResponse 对象
        """
        try:
            from backend.models import ContentListResponse, ContentItemBase
            
            videos, total = self.video_repo.list_videos(limit, offset, sort)
            
            items = [
                ContentItemBase(
                    id=v['id'],
                    title=v['title'],
                    summary=v.get('summary'),
                    source_type=v['source_type'],
                    tags=v.get('tags', []),
                    created_at=v['created_at'],
                    type='video'
                )
                for v in videos
            ]
            
            return ContentListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"获取视频列表错误: {str(e)}")
            raise
    
    def list_archives(self, limit: int, offset: int, sort: str = "recent"):
        """列出网页归档"""
        try:
            from backend.models import ContentListResponse, ContentItemBase
            
            archives, total = self.archive_repo.list_archives(limit, offset, sort)
            
            items = [
                ContentItemBase(
                    id=a['id'],
                    title=a['title'],
                    summary=a.get('summary'),
                    source_type=a['source_type'],
                    tags=a.get('tags', []),
                    created_at=a['created_at'],
                    type='archive'
                )
                for a in archives
            ]
            
            return ContentListResponse(
                items=items,
                total=total,
                limit=limit,
                offset=offset
            )
        except Exception as e:
            logger.error(f"获取归档列表错误: {str(e)}")
            raise
    
    def get_video_detail(self, video_id: int):
        """获取视频详情"""
        try:
            from backend.models import VideoDetailResponse
            
            video = self.video_repo.get_video_by_id(video_id)
            if not video:
                raise ValueError(f"视频 {video_id} 不存在")
            
            # 获取关联的产物（转写、OCR、报告）
            artifacts = self.video_repo.get_artifacts(video_id)
            
            transcript = None
            ocr_text = None
            report = None
            
            for artifact in artifacts:
                artifact_type = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type
                if artifact_type == 'transcript':
                    transcript = artifact.content_text
                elif artifact_type == 'ocr':
                    ocr_text = artifact.content_text
                elif artifact_type == 'report':
                    report = artifact.content_text
            
            # 转换 Video 对象为字典
            video_dict = video.to_dict()
            
            return VideoDetailResponse(
                id=video_dict['id'],
                type='video',
                title=video_dict['title'],
                summary='暂无摘要',
                source_type=video_dict['source_type'],
                source_url=video_dict.get('source_url'),
                created_at=video_dict['created_at'],
                tags=video_dict.get('tags', []),
                transcript=transcript,
                ocr_text=ocr_text,
                report=report,
                duration_seconds=video_dict.get('duration_seconds'),
                file_path=video_dict.get('file_path')
            )
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"获取视频详情错误: {str(e)}")
            raise
    
    def get_archive_detail(self, archive_id: int):
        """获取网页归档详情"""
        try:
            from backend.models import VideoDetailResponse
            
            archive = self.archive_repo.get_archive(archive_id)
            if not archive:
                raise ValueError(f"归档 {archive_id} 不存在")
            
            return VideoDetailResponse(
                id=archive['id'],
                type='archive',
                title=archive['title'],
                summary=archive.get('summary'),
                source_type=archive['source_type'],
                source_url=archive.get('source_url'),
                created_at=archive['created_at'],
                tags=archive.get('tags', []),
                transcript=archive.get('content'),
                ocr_text=None,
                report=archive.get('content')
            )
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"获取归档详情错误: {str(e)}")
            raise

# #endregion

# #region 统计服务

class StatsService:
    """统计业务服务"""
    
    def __init__(self, stats_repo, tag_repo, video_repo, archive_repo):
        self.stats_repo = stats_repo
        self.tag_repo = tag_repo
        self.video_repo = video_repo
        self.archive_repo = archive_repo
    
    def get_statistics(self):
        """获取数据库统计信息"""
        try:
            from backend.models import StatsResponse, TagResponse
            
            # 获取数量统计
            total_videos = self.video_repo.count()
            total_archives = self.archive_repo.count()
            total_tags = self.tag_repo.count()
            
            # 获取热门标签（前10）
            top_tags_data = self.tag_repo.get_top_tags(limit=10)
            top_tags = [
                TagResponse(
                    id=tag['id'],
                    name=tag['name'],
                    count=tag['count'],
                    category=tag.get('category')
                )
                for tag in top_tags_data
            ]
            
            # 计算平均视频时长
            avg_duration = self.video_repo.get_average_duration()
            
            return StatsResponse(
                total_videos=total_videos,
                total_archives=total_archives,
                total_tags=total_tags,
                top_tags=top_tags,
                average_video_duration=avg_duration,
                last_updated=datetime.now()
            )
        except Exception as e:
            logger.error(f"获取统计信息错误: {str(e)}")
            raise
    
    def get_all_tags(self, limit: int = 50):
        """获取所有标签"""
        try:
            from backend.models import TagResponse
            
            tags_data = self.tag_repo.get_all_tags(limit)
            return [
                TagResponse(
                    id=tag['id'],
                    name=tag['name'],
                    count=tag['count'],
                    category=tag.get('category')
                )
                for tag in tags_data
            ]
        except Exception as e:
            logger.error(f"获取标签错误: {str(e)}")
            raise

# #endregion

# #endregion
