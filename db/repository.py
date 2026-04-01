"""
数据访问层（Repository Pattern）
提供 CRUD 操作和业务逻辑
"""
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from .schema import get_connection
from .models import (
    Video, Artifact, Tag, Topic, TimelineEntry,
    SourceType, ProcessingStatus, ArtifactType
)
from .tag_filters import filter_display_tags, get_hidden_tag_sql, split_display_tags

#region 常量定义

# 所有网页归档类型的来源标识（新增平台时只需在此处维护）
WEB_SOURCES = ('web_archive', 'zhihu', 'reddit', 'twitter', 'xiaohongshu')

#endregion


class VideoRepository:
    """视频数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def calculate_content_hash(self, file_path: str) -> str:
        """计算视频文件的 SHA256 hash"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # 分块读取，避免大文件占用内存
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def create_video(self, video: Video) -> int:
        """
        创建视频记录
        
        Args:
            video: Video 对象
        
        Returns:
            int: 新创建记录的 ID
        
        Raises:
            sqlite3.IntegrityError: 如果 content_hash 已存在
        """
        with self._get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO videos (
                    content_hash, video_id, source_type, source_url, 
                    platform_title, title, duration_seconds, 
                    file_path, file_size_bytes, processing_config, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                video.content_hash,
                video.video_id,
                video.source_type.value if isinstance(video.source_type, SourceType) else video.source_type,
                video.source_url,
                video.platform_title,
                video.title,
                video.duration_seconds,
                video.file_path,
                video.file_size_bytes,
                json.dumps(video.processing_config) if video.processing_config else None,
                video.status.value if isinstance(video.status, ProcessingStatus) else video.status
            ))
            
            video_id = cursor.lastrowid
            return video_id
    
    def get_video_by_id(self, video_id: int) -> Optional[Video]:
        """根据 ID 获取视频"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM videos WHERE id = ?
            """, (video_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_video(row, conn)
    
    def get_video_by_hash(self, content_hash: str) -> Optional[Video]:
        """根据 content_hash 获取视频（用于去重）"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM videos WHERE content_hash = ?
            """, (content_hash,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_video(row, conn)
    
    def get_video_by_source_url(self, source_url: str) -> Optional[Video]:
        """根据 source_url 获取视频（用于检查是否已下载）"""
        with self._get_conn() as conn:
            # 支持模糊匹配，因为同一视频可能有不同的URL格式
            # 例如 bilibili.com/video/BVxxx 和 b23.tv/xxx
            cursor = conn.execute("""
                SELECT * FROM videos WHERE source_url = ?
            """, (source_url,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_video(row, conn)
    
    def get_video_by_video_id(self, platform: str, video_id: str) -> Optional[Video]:
        """
        根据平台和视频ID获取视频（用于检查是否已下载）
        
        Args:
            platform: 平台名称 (bilibili, youtube, xiaohongshu等)
            video_id: 平台视频ID (BVxxx, xxx等)
        """
        with self._get_conn() as conn:
            # 在 source_url 中搜索视频ID
            cursor = conn.execute("""
                SELECT * FROM videos 
                WHERE source_type = ? AND source_url LIKE ?
            """, (platform, f"%{video_id}%"))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return self._row_to_video(row, conn)
    
    def update_video_status(self, video_id: int, status: ProcessingStatus, 
                           error_message: Optional[str] = None):
        """更新视频处理状态"""
        with self._get_conn() as conn:
            if status == ProcessingStatus.COMPLETED:
                conn.execute("""
                    UPDATE videos 
                    SET status = ?, processed_at = CURRENT_TIMESTAMP, error_message = ?
                    WHERE id = ?
                """, (status.value, error_message, video_id))
            else:
                conn.execute("""
                    UPDATE videos 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                """, (status.value, error_message, video_id))
    
    def update_video_metadata(self, video_id: int, duration_seconds: Optional[float] = None,
                             title: Optional[str] = None, platform_title: Optional[str] = None):
        """更新视频元数据（时长、标题等）"""
        with self._get_conn() as conn:
            updates = []
            params = []
            
            if duration_seconds is not None:
                updates.append("duration_seconds = ?")
                params.append(duration_seconds)
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            
            if platform_title is not None:
                updates.append("platform_title = ?")
                params.append(platform_title)
            
            if updates:
                params.append(video_id)
                sql = f"UPDATE videos SET {', '.join(updates)} WHERE id = ?"
                conn.execute(sql, params)
    
    def delete_video(self, video_id: int) -> bool:
        """
        删除视频记录及其所有关联数据
        
        Args:
            video_id: 视频ID
            
        Returns:
            bool: 是否成功删除
        """
        with self._get_conn() as conn:
            # 检查视频是否存在
            cursor = conn.execute("SELECT id FROM videos WHERE id = ?", (video_id,))
            if not cursor.fetchone():
                return False
            
            # 删除关联数据（由于外键约束，这些会自动级联删除，但我们显式执行以确保）
            # 1. 删除标签关联
            conn.execute("DELETE FROM video_tags WHERE video_id = ?", (video_id,))
            
            # 2. 删除主题
            conn.execute("DELETE FROM topics WHERE video_id = ?", (video_id,))
            
            # 3. 删除文件（artifacts）
            conn.execute("DELETE FROM artifacts WHERE video_id = ?", (video_id,))
            
            # 4. 删除全文搜索内容
            conn.execute("DELETE FROM fts_content WHERE video_id = ?", (video_id,))
            
            # 5. 最后删除视频记录
            conn.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            
            return True
    
    def save_artifact(self, artifact: Artifact) -> int:
        """保存处理产物（转写/OCR/报告）"""
        with self._get_conn() as conn:
            # 计算字符数和词数
            char_count = len(artifact.content_text)
            word_count = len(artifact.content_text.split())
            
            cursor = conn.execute("""
                INSERT INTO artifacts (
                    video_id, artifact_type, content_text, content_json,
                    file_path, model_name, model_params, 
                    char_count, word_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                artifact.video_id,
                artifact.artifact_type.value if isinstance(artifact.artifact_type, ArtifactType) else artifact.artifact_type,
                artifact.content_text,
                json.dumps(artifact.content_json, ensure_ascii=False) if artifact.content_json else None,
                artifact.file_path,
                artifact.model_name,
                json.dumps(artifact.model_params) if artifact.model_params else None,
                char_count,
                word_count
            ))
            
            return cursor.lastrowid
    
    def get_artifacts(self, video_id: int, 
                     artifact_type: Optional[ArtifactType] = None) -> List[Artifact]:
        """获取视频的产物"""
        with self._get_conn() as conn:
            if artifact_type:
                cursor = conn.execute("""
                    SELECT * FROM artifacts 
                    WHERE video_id = ? AND artifact_type = ?
                    ORDER BY created_at DESC
                """, (video_id, artifact_type.value))
            else:
                cursor = conn.execute("""
                    SELECT * FROM artifacts 
                    WHERE video_id = ?
                    ORDER BY created_at DESC
                """, (video_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_artifact(row) for row in rows]
    
    def save_tags(self, video_id: int, tag_names: List[str], 
                  source: str = 'auto', confidence: float = 1.0):
        """
        保存视频标签
        
        Args:
            video_id: 视频ID
            tag_names: 标签名称列表
            source: 'auto' 或 'manual'
            confidence: 置信度（仅对自动标签有效）
        """
        with self._get_conn() as conn:
            for tag_name in filter_display_tags(tag_names):
                # 先查找或创建标签
                cursor = conn.execute("""
                    SELECT id FROM tags WHERE name = ? COLLATE NOCASE
                """, (tag_name,))
                row = cursor.fetchone()
                
                if row:
                    tag_id = row['id']
                else:
                    # 创建新标签
                    cursor = conn.execute("""
                        INSERT INTO tags (name) VALUES (?)
                    """, (tag_name,))
                    tag_id = cursor.lastrowid
                
                # 关联视频和标签（忽略重复）
                try:
                    conn.execute("""
                        INSERT INTO video_tags (video_id, tag_id, source, confidence)
                        VALUES (?, ?, ?, ?)
                    """, (video_id, tag_id, source, confidence))
                except sqlite3.IntegrityError:
                    # 已存在，跳过（唯一约束冲突）
                    pass
    
    def get_video_tags(self, video_id: int) -> List[str]:
        """获取视频的标签"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT t.name FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                WHERE vt.video_id = ?
                ORDER BY t.name
            """, (video_id,))
            
            return filter_display_tags(row['name'] for row in cursor.fetchall())
    
    def list_videos_with_summary(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """列出所有视频及其摘要信息
        
        Args:
            limit: 返回视频数量
            offset: 分页偏移量
            
        Returns:
            包含视频信息的字典列表，每个字典包含：
            - id: 视频ID
            - title: 标题
            - source_type: 来源类型
            - duration: 时长（秒）
            - tags: 标签列表
            - summary: 内容摘要（来自report）
            - created_at: 创建时间
        """
        with self._get_conn() as conn:
            # 使用子查询避免 JOIN 导致的重复，获取最新的 report
            cursor = conn.execute("""
                SELECT 
                    v.id, v.title, v.source_type, v.duration_seconds, v.created_at,
                    (
                        SELECT GROUP_CONCAT(t.name, ', ')
                        FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE vt.video_id = v.id
                    ) as tags,
                    (
                        SELECT a.content_text
                        FROM artifacts a
                        WHERE a.video_id = v.id AND a.artifact_type = 'summary'
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as explicit_summary
                FROM videos v
                ORDER BY v.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                # 提取摘要（使用AI生成的摘要章节）
                summary = row['explicit_summary'] if ('explicit_summary' in row.keys() and row['explicit_summary']) else '暂无摘要'
                
                results.append({
                    'id': row['id'],
                    'title': row['title'] or '未命名',
                    'source_type': row['source_type'],
                    'duration': row['duration_seconds'] or 0,
                    'tags': split_display_tags(row['tags']),
                    'summary': summary,
                    'created_at': row['created_at']
                })
            
            return results
    
    def save_topics(self, video_id: int, topics: List[Topic]) -> List[int]:
        """批量保存主题"""
        topic_ids = []
        
        with self._get_conn() as conn:
            for topic in topics:
                cursor = conn.execute("""
                    INSERT INTO topics (
                        video_id, title, summary, start_time, end_time,
                        keywords, key_points, sequence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id,
                    topic.title,
                    topic.summary,
                    topic.start_time,
                    topic.end_time,
                    json.dumps(topic.keywords, ensure_ascii=False),
                    json.dumps(topic.key_points, ensure_ascii=False),
                    topic.sequence
                ))
                topic_ids.append(cursor.lastrowid)
        
        return topic_ids
    
    def get_topics(self, video_id: int) -> List[Topic]:
        """获取视频的主题"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT * FROM topics 
                WHERE video_id = ?
                ORDER BY sequence
            """, (video_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_topic(row) for row in rows]
    
    def save_timeline(self, video_id: int, entries: List[TimelineEntry]) -> List[int]:
        """批量保存时间线条目"""
        entry_ids = []
        
        with self._get_conn() as conn:
            for entry in entries:
                cursor = conn.execute("""
                    INSERT INTO timeline_entries (
                        video_id, timestamp_seconds, frame_number,
                        transcript_text, ocr_text, frame_path, is_key_frame
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id,
                    entry.timestamp_seconds,
                    entry.frame_number,
                    entry.transcript_text,
                    entry.ocr_text,
                    entry.frame_path,
                    entry.is_key_frame
                ))
                entry_ids.append(cursor.lastrowid)
        
        return entry_ids
    
    def update_fts_index(self, video_id: int):
        """
        更新全文搜索索引
        在保存所有产物后调用
        """
        with self._get_conn() as conn:
            # 获取视频信息
            video = self.get_video_by_id(video_id)
            if not video:
                return
            
            # 获取所有产物
            artifacts = self.get_artifacts(video_id)
            topics = self.get_topics(video_id)
            tags = self.get_video_tags(video_id)
            
            # 标签拼接成字符串
            tags_str = ' '.join(tags)
            
            # 插入 FTS 索引
            for artifact in artifacts:
                conn.execute("""
                    INSERT INTO fts_content (video_id, source_field, title, content, tags)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    video_id,
                    artifact.artifact_type,
                    video.title,
                    artifact.content_text,
                    tags_str
                ))
            
            # 索引主题
            for topic in topics:
                topic_content = f"{topic.title}\n{topic.summary or ''}"
                conn.execute("""
                    INSERT INTO fts_content (video_id, source_field, title, content, tags)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    video_id,
                    'topic',
                    video.title,
                    topic_content,
                    tags_str
                ))
    
    def count(self) -> int:
        """统计视频总数"""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM videos")
            return cursor.fetchone()['count']
    
    def get_average_duration(self) -> float:
        """获取平均视频时长（秒）"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT AVG(duration_seconds) as avg_duration 
                FROM videos 
                WHERE duration_seconds IS NOT NULL
            """)
            row = cursor.fetchone()
            return row['avg_duration'] or 0.0
    
    def list_videos(self, limit: int = 100, offset: int = 0, sort: str = "recent",
                    tags: Optional[List[str]] = None) -> tuple:
        """
        列出视频，返回 (videos_list, total_count) 元组
        排除网页来源的视频

        Args:
            limit: 数量限制
            offset: 分页偏移
            sort: 排序方式 (recent/oldest/duration)
            tags: 标签过滤列表（任意匹配）

        Returns:
            tuple: (视频字典列表, 总数)
        """
        with self._get_conn() as conn:
            # 构建排序条件
            if sort == "oldest":
                order_by = "ORDER BY v.created_at ASC"
            elif sort == "duration":
                order_by = "ORDER BY v.duration_seconds DESC NULLS LAST"
            else:  # 默认 recent
                order_by = "ORDER BY v.created_at DESC"

            # 构建标签过滤条件
            tag_join = ""
            tag_where = ""
            tag_params: list = []
            if tags:
                tag_placeholders = ','.join(['?' for _ in tags])
                tag_join = f"""
                    INNER JOIN video_tags vt_filter ON vt_filter.video_id = v.id
                    INNER JOIN tags t_filter ON t_filter.id = vt_filter.tag_id
                        AND t_filter.name IN ({tag_placeholders})
                """
                tag_params = list(tags)

            # 统计总数（排除网页）
            placeholders = ','.join(['?' for _ in WEB_SOURCES])
            count_query = f"""
                SELECT COUNT(DISTINCT v.id) as count FROM videos v
                {tag_join}
                WHERE v.source_type NOT IN ({placeholders})
                {tag_where}
            """
            cursor = conn.execute(count_query, tag_params + list(WEB_SOURCES))
            total = cursor.fetchone()['count']

            # 获取视频列表及其摘要（排除网页）
            query = f"""
                SELECT DISTINCT
                    v.id, v.title, v.source_type, v.duration_seconds, v.file_size_bytes, v.created_at,
                    (
                        SELECT GROUP_CONCAT(t.name, ', ')
                        FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE vt.video_id = v.id
                    ) as tags,
                    (
                        SELECT a.content_text
                        FROM artifacts a
                        WHERE a.video_id = v.id AND a.artifact_type = 'summary'
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as explicit_summary
                FROM videos v
                {tag_join}
                WHERE v.source_type NOT IN ({placeholders})
                {tag_where}
                {order_by}
                LIMIT ? OFFSET ?
            """

            params = tag_params + list(WEB_SOURCES) + [limit, offset]
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                # 提取摘要
                summary = row['explicit_summary'] if ('explicit_summary' in row.keys() and row['explicit_summary']) else '暂无摘要'
                
                results.append({
                    'id': row['id'],
                    'title': row['title'] or '未命名',
                    'source_type': row['source_type'],
                    'duration': row['duration_seconds'] or 0,
                    'file_size': row['file_size_bytes'] or 0,
                    'tags': split_display_tags(row['tags']),
                    'summary': summary,
                    'created_at': row['created_at'],
                    'type': 'video'
                })
            
            return results, total
    
    # 辅助方法
    def _row_to_video(self, row: dict, conn) -> Video:
        """将数据库行转换为 Video 对象"""
        video = Video(
            id=row['id'],
            content_hash=row['content_hash'],
            video_id=row['video_id'],
            source_type=SourceType(row['source_type']),
            source_url=row['source_url'],
            platform_title=row['platform_title'],
            title=row['title'],
            duration_seconds=row['duration_seconds'],
            file_path=row['file_path'],
            file_size_bytes=row['file_size_bytes'],
            processing_config=row['processing_config'] if row['processing_config'] else None,
            status=ProcessingStatus(row['status']),
            error_message=row['error_message'],
            created_at=row['created_at'] if isinstance(row['created_at'], datetime) else (datetime.fromisoformat(row['created_at']) if row['created_at'] else None),
            processed_at=row['processed_at'] if isinstance(row['processed_at'], datetime) else (datetime.fromisoformat(row['processed_at']) if row['processed_at'] else None),
            updated_at=row['updated_at'] if isinstance(row['updated_at'], datetime) else (datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None),
        )
        
        # 加载标签（直接使用传入的 conn，避免嵌套连接导致 database is locked）
        cursor = conn.execute("""
            SELECT t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
            ORDER BY t.name
        """, (row['id'],))
        video.tags = filter_display_tags(r['name'] for r in cursor.fetchall())

        return video
    
    def _row_to_artifact(self, row: dict) -> Artifact:
        """将数据库行转换为 Artifact 对象"""
        return Artifact(
            id=row['id'],
            video_id=row['video_id'],
            artifact_type=ArtifactType(row['artifact_type']),
            content_text=row['content_text'],
            content_json=row['content_json'] if row['content_json'] else None,
            file_path=row['file_path'],
            model_name=row['model_name'],
            model_params=row['model_params'] if row['model_params'] else None,
            char_count=row['char_count'],
            word_count=row['word_count'],
            created_at=row['created_at'] if isinstance(row['created_at'], datetime) else (datetime.fromisoformat(row['created_at']) if row['created_at'] else None),
        )
    
    def _row_to_topic(self, row: dict) -> Topic:
        """将数据库行转换为 Topic 对象"""
        return Topic(
            id=row['id'],
            video_id=row['video_id'],
            title=row['title'],
            summary=row['summary'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            keywords=row['keywords'] if row['keywords'] else [],
            key_points=row['key_points'] if row['key_points'] else [],
            sequence=row['sequence'],
            created_at=row['created_at'] if isinstance(row['created_at'], datetime) else (datetime.fromisoformat(row['created_at']) if row['created_at'] else None),
        )


#region 网页归档存储库

class ArchiveRepository:
    """归档内容数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_archive(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """获取归档内容"""
        with self._get_conn() as conn:
            placeholders = ','.join(['?' for _ in WEB_SOURCES])
            cursor = conn.execute(f"""
                SELECT * FROM videos
                WHERE id = ? AND source_type IN ({placeholders})
            """, (archive_id, *WEB_SOURCES))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 获取所有 artifact
            cursor = conn.execute("""
                SELECT artifact_type, content_text FROM artifacts
                WHERE video_id = ?
            """, (archive_id,))
            artifacts = cursor.fetchall()
            
            transcript_text = None
            report_text = None
            ocr_text = None
            summary_text = None
            
            for art in artifacts:
                atype = art['artifact_type']
                if atype == 'transcript':
                    transcript_text = art['content_text']
                elif atype == 'report':
                    report_text = art['content_text']
                elif atype == 'ocr':
                    ocr_text = art['content_text']
                elif atype == 'summary':
                    summary_text = art['content_text']
            
            content_text = report_text or transcript_text or '暂无内容'
            
            result = {
                'id': row['id'],
                'title': row['title'],
                'source_type': row['source_type'],
                'source_url': row['source_url'],
                'file_path': row['file_path'],
                'created_at': row['created_at'],
                'content': content_text,
                'transcript': transcript_text,
                'report': report_text,
                'ocr_text': ocr_text,
                'summary': summary_text if summary_text else '暂无摘要'
            }
            
            # 获取标签
            cursor = conn.execute("""
                SELECT t.name FROM tags t
                JOIN video_tags vt ON t.id = vt.tag_id
                WHERE vt.video_id = ?
            """, (archive_id,))
            result['tags'] = filter_display_tags(r['name'] for r in cursor.fetchall())
            
            return result
    
    def list_archives(self, limit: int = 20, offset: int = 0, sort: str = "recent",
                      tags: Optional[List[str]] = None) -> tuple:
        """
        列出网页归档

        Args:
            limit: 数量限制
            offset: 分页偏移
            sort: 排序方式 (recent/oldest)
            tags: 标签过滤列表（任意匹配）

        Returns:
            tuple: (归档列表, 总数)
        """
        with self._get_conn() as conn:
            # 排序条件
            if sort == "oldest":
                order_by = "ORDER BY v.created_at ASC"
            else:  # 默认 recent
                order_by = "ORDER BY v.created_at DESC"

            # 构建标签过滤条件
            tag_join = ""
            tag_params: list = []
            if tags:
                tag_placeholders = ','.join(['?' for _ in tags])
                tag_join = f"""
                    INNER JOIN video_tags vt_filter ON vt_filter.video_id = v.id
                    INNER JOIN tags t_filter ON t_filter.id = vt_filter.tag_id
                        AND t_filter.name IN ({tag_placeholders})
                """
                tag_params = list(tags)

            # 统计网页归档总数
            placeholders = ','.join(['?' for _ in WEB_SOURCES])
            count_query = f"""
                SELECT COUNT(DISTINCT v.id) as count FROM videos v
                {tag_join}
                WHERE v.source_type IN ({placeholders})
            """
            cursor = conn.execute(count_query, tag_params + list(WEB_SOURCES))
            total = cursor.fetchone()['count']

            # 获取归档列表（包含摘要和元数据）
            query = f"""
                SELECT DISTINCT
                    v.id, v.title, v.source_type, v.source_url, v.file_size_bytes, v.created_at,
                    (
                        SELECT GROUP_CONCAT(t.name, ', ')
                        FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE vt.video_id = v.id
                    ) as tags,
                    (
                        SELECT a.content_text
                        FROM artifacts a
                        WHERE a.video_id = v.id AND a.artifact_type = 'summary'
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as explicit_summary,
                    (
                        SELECT a.content_text
                        FROM artifacts a
                        WHERE a.video_id = v.id AND a.artifact_type IN ('report', 'transcript')
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as content
                FROM videos v
                {tag_join}
                WHERE v.source_type IN ({placeholders})
                {order_by}
                LIMIT ? OFFSET ?
            """

            params = tag_params + list(WEB_SOURCES) + [limit, offset]
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                # 正确提取摘要
                summary = row['explicit_summary'] if ('explicit_summary' in row.keys() and row['explicit_summary']) else '暂无摘要'
                
                results.append({
                    'id': row['id'],
                    'title': row['title'] or '未命名',
                    'source_type': row['source_type'],
                    'source_url': row['source_url'],
                    'file_size': row['file_size_bytes'] or 0,
                    'tags': split_display_tags(row['tags']),
                    'summary': summary,
                    'created_at': row['created_at'],
                    'type': 'archive'
                })
            
            return results, total
    
    def count(self) -> int:
        """统计归档总数"""
        with self._get_conn() as conn:
            placeholders = ','.join(['?' for _ in WEB_SOURCES])
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM videos WHERE source_type IN ({placeholders})", WEB_SOURCES)
            return cursor.fetchone()['count']

#endregion

#region 标签存储库

class TagRepository:
    """标签数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def count(self) -> int:
        """统计标签总数"""
        with self._get_conn() as conn:
            visible_clause, visible_params = get_hidden_tag_sql("name")
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM tags WHERE {visible_clause}",
                visible_params
            )
            return cursor.fetchone()['count']
    
    def get_all_tags(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取所有标签"""
        with self._get_conn() as conn:
            visible_clause, visible_params = get_hidden_tag_sql("name")
            cursor = conn.execute(f"""
                SELECT id, name, category, count FROM tags
                WHERE {visible_clause}
                ORDER BY count DESC, name ASC
                LIMIT ?
            """, [*visible_params, limit])
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'count': row['count'] or 0,
                    'category': row['category']
                }
                for row in cursor.fetchall()
            ]
    
    def get_top_tags(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取热门标签"""
        with self._get_conn() as conn:
            visible_clause, visible_params = get_hidden_tag_sql("t.name")
            cursor = conn.execute(f"""
                SELECT 
                    t.id, t.name, t.category,
                    COUNT(vt.video_id) as count
                FROM tags t
                LEFT JOIN video_tags vt ON t.id = vt.tag_id
                WHERE {visible_clause}
                GROUP BY t.id
                ORDER BY count DESC, t.name ASC
                LIMIT ?
            """, [*visible_params, limit])
            
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'count': row['count'],
                    'category': row['category']
                }
                for row in cursor.fetchall()
            ]
    
    def get_tag_stats(self) -> Dict[str, int]:
        """获取标签统计"""
        with self._get_conn() as conn:
            visible_clause, visible_params = get_hidden_tag_sql("name")
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM tags WHERE {visible_clause}",
                visible_params
            )
            total_tags = cursor.fetchone()['count']
            
            used_clause, used_params = get_hidden_tag_sql("t.name")
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT vt.tag_id) as count
                FROM video_tags vt
                JOIN tags t ON vt.tag_id = t.id
                WHERE {used_clause}
            """, used_params)
            used_tags = cursor.fetchone()['count']
            
            return {
                'total_tags': total_tags,
                'used_tags': used_tags
            }

#endregion

#region 搜索存储库

class SearchRepository:
    """全文搜索数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def search(self, query: str, tags: Optional[List[str]] = None,
               source_type: Optional[str] = None, limit: int = 20, offset: int = 0) -> tuple:
        """执行全文搜索"""
        with self._get_conn() as conn:
            # 构建 FTS 查询
            results = []
            
            # 简单的全文搜索（不支持 FTS5 高级句法时的降级方案）
            sql = """
                SELECT DISTINCT 
                    v.id, v.title, v.source_type, v.created_at,
                    f.source_field,
                    (
                        SELECT GROUP_CONCAT(t.name, ', ')
                        FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE vt.video_id = v.id
                    ) as tags,
                    (
                        SELECT a.content_text
                        FROM artifacts a
                        WHERE a.video_id = v.id AND a.artifact_type = 'summary'
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as explicit_summary
                FROM videos v
                LEFT JOIN fts_content f ON v.id = f.video_id
                WHERE 1=1
            """
            
            params = []
            
            # 关键词搜索
            if query:
                sql += " AND (v.title LIKE ? OR f.content LIKE ?)"
                wildcard_query = f"%{query}%"
                params.extend([wildcard_query, wildcard_query])
            
            # 标签过滤
            if tags and len(tags) > 0:
                placeholders = ','.join(['?' for _ in tags])
                sql += f"""
                    AND v.id IN (
                        SELECT DISTINCT vt.video_id FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE t.name IN ({placeholders})
                    )
                """
                params.extend(tags)
            
            # 来源类型过滤
            if source_type:
                sql += " AND v.source_type = ?"
                params.append(source_type)
            
            # 统计总数
            count_sql = "SELECT COUNT(*) as count FROM (" + sql + ") AS search_results"
            cursor = conn.execute(count_sql, params)
            total = cursor.fetchone()['count']
            
            # 分页和排序
            sql += " ORDER BY v.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(sql, params)
            
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'type': 'archive' if row['source_type'] in WEB_SOURCES else 'video',
                    'title': row['title'],
                    'summary': row['explicit_summary'] if ('explicit_summary' in row.keys() and row['explicit_summary']) else '暂无摘要',
                    'source_type': row['source_type'],
                    'tags': split_display_tags(row['tags']),
                    'created_at': row['created_at']
                })
            
            return results, total
    
    def index_content(self, video_id: int, content: str, metadata: Dict[str, Any]) -> bool:
        """索引内容"""
        return True

#endregion

#region 统计存储库

class StatsRepository:
    """统计数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接的上下文管理器"""
        conn = get_connection(self.db_path)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取全站统计"""
        with self._get_conn() as conn:
            # 统计视频
            placeholders = ','.join(['?' for _ in WEB_SOURCES])
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM videos WHERE source_type NOT IN ({placeholders})", WEB_SOURCES)
            total_videos = cursor.fetchone()['count']

            # 统计归档
            cursor = conn.execute(f"SELECT COUNT(*) as count FROM videos WHERE source_type IN ({placeholders})", WEB_SOURCES)
            total_archives = cursor.fetchone()['count']
            
            # 统计标签
            visible_clause, visible_params = get_hidden_tag_sql("name")
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM tags WHERE {visible_clause}",
                visible_params
            )
            total_tags = cursor.fetchone()['count']
            
            # 统计产物
            cursor = conn.execute("SELECT COUNT(*) as count FROM artifacts")
            total_artifacts = cursor.fetchone()['count']
            
            return {
                "total_videos": total_videos,
                "total_archives": total_archives,
                "total_artifacts": total_artifacts,
                "total_tags": total_tags
            }
    
    def get_time_series_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """获取时间序列统计数据"""
        with self._get_conn() as conn:
            cursor = conn.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count,
                    source_type
                FROM videos
                WHERE created_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(created_at), source_type
                ORDER BY date ASC
            """, (days,))
            
            return [
                {
                    'date': row['date'],
                    'count': row['count'],
                    'source_type': row['source_type']
                }
                for row in cursor.fetchall()
            ]

#endregion
