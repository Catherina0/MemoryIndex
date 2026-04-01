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
        执行全文搜索（使用 Whoosh+FTS5 混合搜索引擎）

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
            from backend.models import SearchResultResponse, SearchResultItem
            from db.repository import WEB_SOURCES

            # 调用 Whoosh+FTS5 混合搜索（不分页，用于获取 total）
            all_results = self.search_repo.search(
                query=query,
                tags=tags,
                limit=9999,
                offset=0
            )

            # source_type 过滤（search.py 不支持此参数，在服务层过滤）
            if source_type:
                all_results = [r for r in all_results if r.source_type == source_type]

            total = len(all_results)
            paginated = all_results[offset:offset + limit]

            # 转换 SearchResult → SearchResultItem
            items = []
            for r in paginated:
                content_type = 'archive' if r.source_type in WEB_SOURCES else 'video'
                item = SearchResultItem(
                    id=r.video_id,
                    type=content_type,
                    title=r.video_title,
                    summary=r.matched_snippet or '暂无摘要',
                    source_type=r.source_type or '',
                    tags=r.tags if r.tags else [],
                    created_at=r.created_at,
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
    
    def list_videos(self, limit: int, offset: int, sort: str = "recent",
                    tags: Optional[List[str]] = None):
        """
        列出视频

        Args:
            limit: 数量限制
            offset: 分页偏移
            sort: 排序方式 (recent/oldest/duration)
            tags: 标签过滤列表

        Returns:
            ContentListResponse 对象
        """
        try:
            from backend.models import ContentListResponse, ContentItemBase

            videos, total = self.video_repo.list_videos(limit, offset, sort, tags=tags)
            
            items = [
                ContentItemBase(
                    id=v['id'],
                    title=v['title'],
                    summary=v.get('summary'),
                    source_type=v['source_type'],
                    tags=v.get('tags', []),
                    created_at=v['created_at'],
                    type=v.get('type', 'video'),
                    duration=v.get('duration'),
                    file_size=v.get('file_size')
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
    
    def list_archives(self, limit: int, offset: int, sort: str = "recent",
                      tags: Optional[List[str]] = None):
        """列出网页归档"""
        try:
            from backend.models import ContentListResponse, ContentItemBase

            archives, total = self.archive_repo.list_archives(limit, offset, sort, tags=tags)
            
            items = [
                ContentItemBase(
                    id=a['id'],
                    title=a['title'],
                    summary=a.get('summary'),
                    source_type=a['source_type'],
                    source_url=a.get('source_url'),
                    tags=a.get('tags', []),
                    created_at=a['created_at'],
                    type=a.get('type', 'archive'),
                    file_size=a.get('file_size')
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
            summary_text = None
            
            for artifact in artifacts:
                artifact_type = artifact.artifact_type.value if hasattr(artifact.artifact_type, 'value') else artifact.artifact_type
                if artifact_type == 'transcript':
                    transcript = artifact.content_text
                    if artifact.content_json and 'segments' in artifact.content_json:
                        segments = artifact.content_json['segments']
                        if isinstance(segments, list) and len(segments) > 0:
                            formatted_segments = []
                            for seg in segments:
                                start = seg.get('start', 0)
                                end = seg.get('end', 0)
                                text = seg.get('text', '').strip()
                                
                                start_m, start_s = divmod(int(start), 60)
                                end_m, end_s = divmod(int(end), 60)
                                time_str = f"[{start_m:02d}:{start_s:02d} - {end_m:02d}:{end_s:02d}]"
                                formatted_segments.append(f"**{time_str}**  \n{text}")
                            
                            transcript = "\n\n".join(formatted_segments)
                elif artifact_type == 'ocr':
                    ocr_text = artifact.content_text
                elif artifact_type == 'report':
                    report = artifact.content_text
                elif artifact_type == 'summary':
                    summary_text = artifact.content_text
            
            # 转换 Video 对象为字典
            video_dict = video.to_dict()
            
            # 查找并读取该目录下的 README.md (如果存在)
            readme_text = None
            if video_dict.get('file_path'):
                project_root = Path(__file__).parent.parent
                vid_path = project_root / video_dict['file_path']
                # file_path might be the mp4 file or the directory itself. Let's find the parent dir or if it's a directory
                readme_path = None
                
                # Check for mp4 or dir
                if vid_path.is_file():
                    # 查找对应 output 目录下的 README.md
                    import sqlite3
                    with self.video_repo._get_conn() as conn:
                        cursor = conn.execute("SELECT content_hash FROM videos WHERE id = ?", (video_id,))
                        row = cursor.fetchone()
                        if row:
                            # 尝试在 output 目录下寻找包含该内容或者相关结构的可能目录
                            # 简化起见，直接在 output 下寻找包含相同 hash 相关的文件夹？或用视频ID
                            pass
                else:
                    # 如果 vid_path 是个目录 (对于有些记录可能填的是目录)
                    if vid_path.is_dir():
                        readme_path = vid_path / "README.md"
                
                # 另外一种找 README.md 的方式：所有生成物都在 output/xxx 目录下，其实对于视频一般是存在 output 某目录。
                # 我们的 artifacts 有 file_path，通过 artifact 的 file_path 更容易找到父目录！
                # 遍历 artifacts，看有没有文件在 output 目录
                for artifact in artifacts:
                    if artifact.file_path:
                        a_path = project_root / artifact.file_path
                        if a_path.exists():
                            possible_readme = a_path.parent / "README.md"
                            if possible_readme.exists():
                                readme_path = possible_readme
                                break
                                
                if readme_path and readme_path.exists():
                    try:
                        readme_text = readme_path.read_text(encoding='utf-8')
                    except Exception as e:
                        logger.warning(f"无法读取 README.md: {e}")

            return VideoDetailResponse(
                id=video_dict['id'],
                type='video',
                title=video_dict['title'],
                summary=summary_text if summary_text else '暂无摘要',
                source_type=video_dict['source_type'],
                source_url=video_dict.get('source_url'),
                created_at=video_dict['created_at'],
                tags=video_dict.get('tags', []),
                transcript=transcript,
                ocr_text=ocr_text,
                report=report,
                readme_text=readme_text,
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
                
            raw_archive = None
            readme_text = None
            if archive.get('file_path'):
                project_root = Path(__file__).parent.parent
                arc_path = project_root / archive['file_path']
                logger.info(f"[Archive {archive_id}] Attempting to load files from: {arc_path}, exists={arc_path.exists()}")
                if arc_path.is_dir():
                    raw_path = arc_path / "archive_raw.md"
                    logger.info(f"[Archive {archive_id}] Checking archive_raw.md at: {raw_path}, exists={raw_path.exists()}")
                    if raw_path.exists():
                        try:
                            raw_archive = raw_path.read_text(encoding='utf-8')
                            logger.info(f"[Archive {archive_id}] Successfully loaded archive_raw.md ({len(raw_archive)} bytes)")
                        except Exception as e:
                            logger.warning(f"[Archive {archive_id}] 无法读取 archive_raw.md: {e}")
                    
                    readme_path = arc_path / "README.md"
                    logger.info(f"[Archive {archive_id}] Checking README.md at: {readme_path}, exists={readme_path.exists()}")
                    if readme_path.exists():
                        try:
                            readme_text = readme_path.read_text(encoding='utf-8')
                            logger.info(f"[Archive {archive_id}] Successfully loaded README.md ({len(readme_text)} bytes)")
                        except Exception as e:
                            logger.warning(f"[Archive {archive_id}] 无法读取 README.md: {e}")
                else:
                    logger.warning(f"[Archive {archive_id}] file_path is not a directory: {arc_path}")
            
            return VideoDetailResponse(
                id=archive['id'],
                type='archive',
                title=archive['title'],
                summary=archive.get('summary'),
                source_type=archive['source_type'],
                source_url=archive.get('source_url'),
                created_at=archive['created_at'],
                tags=archive.get('tags', []),
                transcript=archive.get('transcript'),
                ocr_text=archive.get('ocr_text'),
                report=archive.get('report'),
                raw_archive=raw_archive,
                readme_text=readme_text,
                file_path=archive.get('file_path')
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

# #region 导入服务

class ImportService:
    """链接导入业务服务"""
    
    def __init__(self, video_repo, archive_repo):
        self.video_repo = video_repo
        self.archive_repo = archive_repo
        self.web_sources = ('web_archive', 'zhihu', 'reddit', 'twitter', 'xiaohongshu')
    
    def detect_url_type(self, url: str) -> str:
        """
        自动检测 URL 类型
        
        Args:
            url: 输入的 URL
        
        Returns:
            'video' 或 'archive'
        """
        url_lower = url.lower()
        
        # 视频平台常见域名
        video_domains = [
            'youtube.com', 'youtu.be',
            'bilibili.com', 'b23.tv',
            'vimeo.com',
            'dailymotion.com',
            'qq.com/video',
            'iqiyi.com',
            'douyin.com',
            'tiktok.com',
            'xiaohongshu.com', 'xhslink.com',
        ]
        
        for domain in video_domains:
            if domain in url_lower:
                return 'video'
        
        # 默认当作网页归档
        return 'archive'
    
    def import_content(self, url: str, content_type: str = 'auto', 
                      use_ocr: bool = False) -> dict:
        """
        导入内容（URL）
        
        Args:
            url: 内容 URL
            content_type: 内容类型 ('auto'/'video'/'archive')
            use_ocr: 是否启用 OCR
        
        Returns:
            {
                'status': 'queued' | 'error',
                'task_id': str,
                'content_id': int | None,
                'message': str
            }
        """
        try:
            from backend.task_manager import get_task_manager
            
            # URL 验证
            if not self._is_valid_url(url):
                return {
                    'status': 'error',
                    'task_id': None,
                    'content_id': None,
                    'message': '无效的 URL 格式'
                }
            
            # 自动检测内容类型
            if content_type == 'auto':
                detected_type = self.detect_url_type(url)
                content_type = detected_type
            
            # 创建并注册任务
            task_manager = get_task_manager()
            task_id = task_manager.create_task(
                task_type=content_type,
                url=url,
                use_ocr=use_ocr
            )
            
            # 返回任务 ID
            if content_type == 'video':
                logger.info(f"📹 [导入] 视频任务已创建 (Task: {task_id}, URL: {url}, OCR: {use_ocr})")
            else:
                logger.info(f"🕸️  [导入] 网页任务已创建 (Task: {task_id}, URL: {url})")
            
            return {
                'status': 'queued',
                'task_id': task_id,
                'content_id': None,
                'message': f'✅ 已创建 {content_type} 处理任务 (ID: {task_id})',
                'content_type': content_type,
                'use_ocr': use_ocr
            }
        
        except Exception as e:
            logger.error(f"❌ 导入错误: {str(e)}")
            return {
                'status': 'error',
                'task_id': None,
                'content_id': None,
                'message': f'导入失败: {str(e)}'
            }
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """验证 URL 格式"""
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme in ('http', 'https'), result.netloc])
        except (ValueError, AttributeError):
            return False

# #endregion

# #endregion
