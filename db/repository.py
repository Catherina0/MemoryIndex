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


def extract_summary_from_report(report_text: str) -> str:
    """从AI报告中提取摘要（不超过50字）"""
    if not report_text:
        return "暂无摘要"
    
    # 查找摘要部分
    summary_patterns = [
        r'##\s*摘要\s*\n+(.+?)(?:\n\n|\n##)',  # ## 摘要 后的内容
        r'摘要[：:]\s*(.+?)(?:\n\n|\n##)',     # 摘要: 后的内容
    ]
    
    for pattern in summary_patterns:
        matches = re.findall(pattern, report_text, re.DOTALL | re.MULTILINE)
        if matches:
            extracted = matches[0].strip()
            # 移除Markdown格式
            extracted = re.sub(r'\*\*|\*|`|#|\[|\]|\(.*?\)', '', extracted)
            # 移除多余空白
            extracted = ' '.join(extracted.split())
            # 限制长度为50字
            if len(extracted) > 50:
                extracted = extracted[:50] + '...'
            return extracted
    
    # 如果没找到摘要章节，尝试提取第一段非标题内容
    lines = report_text.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('*') and not line.startswith('-') and len(line) > 10:
            # 移除Markdown格式
            line = re.sub(r'\*\*|\*|`|#|\[|\]|\(.*?\)', '', line)
            line = ' '.join(line.split())
            if len(line) > 50:
                return line[:50] + '...'
            return line
    
    return "暂无摘要"


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
    
    def list_videos(self, status: Optional[ProcessingStatus] = None, 
                   source_type: Optional[SourceType] = None,
                   limit: int = 100, offset: int = 0) -> List[Video]:
        """列出视频"""
        with self._get_conn() as conn:
            query = "SELECT * FROM videos WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            if source_type:
                query += " AND source_type = ?"
                params.append(source_type.value)
            
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_video(row, conn) for row in rows]
    
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
            for tag_name in tag_names:
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
            
            return [row['name'] for row in cursor.fetchall()]
    
    def list_videos(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
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
                        WHERE a.video_id = v.id AND a.artifact_type = 'report'
                        ORDER BY a.created_at DESC
                        LIMIT 1
                    ) as report_content
                FROM videos v
                ORDER BY v.created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            results = []
            for row in cursor.fetchall():
                # 提取摘要（使用AI生成的摘要章节）
                summary = extract_summary_from_report(row['report_content']) if row['report_content'] else '暂无摘要'
                
                results.append({
                    'id': row['id'],
                    'title': row['title'] or '未命名',
                    'source_type': row['source_type'],
                    'duration': row['duration_seconds'] or 0,
                    'tags': row['tags'].split(', ') if row['tags'] else [],
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
        
        # 加载标签
        video.tags = self.get_video_tags(row['id'])
        
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
