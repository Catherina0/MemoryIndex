"""
搜索 API
提供全文搜索、标签搜索、主题搜索等功能
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .schema import get_connection
from .models import SearchResult


class SearchField(str, Enum):
    """搜索字段"""
    ALL = 'all'           # 所有字段
    REPORT = 'report'     # 仅报告
    TRANSCRIPT = 'transcript'  # 仅转写
    OCR = 'ocr'           # 仅OCR
    TOPIC = 'topic'       # 仅主题


class SortBy(str, Enum):
    """排序方式"""
    RELEVANCE = 'relevance'  # 相关性（BM25分数）
    DATE = 'date'            # 时间（最新优先）
    DURATION = 'duration'    # 时长
    TITLE = 'title'          # 标题


class SearchRepository:
    """搜索数据访问层"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
    
    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        fields: SearchField = SearchField.ALL,
        limit: int = 20,
        offset: int = 0,
        sort_by: SortBy = SortBy.RELEVANCE,
        min_relevance: float = 0.0,
        group_by_video: bool = True
    ) -> List[SearchResult]:
        """
        全文搜索
        
        Args:
            query: 搜索查询字符串
            tags: 标签过滤（AND逻辑：必须包含所有标签）
            fields: 搜索字段范围
            limit: 返回结果数量
            offset: 分页偏移
            sort_by: 排序方式
            min_relevance: 最小相关性分数（0-1）
            group_by_video: 是否按视频聚合（默认True，每个视频只显示最佳匹配）
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        conn = get_connection(self.db_path)
        
        try:
            # 构建 FTS 查询
            if fields == SearchField.ALL:
                field_filter = ""
            else:
                field_filter = f"AND fts.source_field = '{fields.value}'"
            
            # 标签过滤
            tag_join = ""
            tag_filter = ""
            if tags:
                tag_join = """
                    JOIN video_tags vt ON v.id = vt.video_id
                    JOIN tags t ON vt.tag_id = t.id
                """
                # 使用子查询确保包含所有标签
                tag_placeholders = ','.join(['?'] * len(tags))
                tag_filter = f"""
                    AND v.id IN (
                        SELECT vt2.video_id FROM video_tags vt2
                        JOIN tags t2 ON vt2.tag_id = t2.id
                        WHERE t2.name IN ({tag_placeholders})
                        GROUP BY vt2.video_id
                        HAVING COUNT(DISTINCT t2.id) = {len(tags)}
                    )
                """
            
            # 排序
            if sort_by == SortBy.RELEVANCE:
                order_clause = "ORDER BY fts.rank"
            elif sort_by == SortBy.DATE:
                order_clause = "ORDER BY v.created_at DESC"
            elif sort_by == SortBy.DURATION:
                order_clause = "ORDER BY v.duration_seconds DESC"
            elif sort_by == SortBy.TITLE:
                order_clause = "ORDER BY v.title"
            else:
                order_clause = "ORDER BY fts.rank"
            
            # 主查询
            if group_by_video:
                # 按视频聚合：只返回每个视频的最佳匹配
                # 对于中文查询使用LIKE后备搜索（解决FTS5中文分词问题）
                use_like = len(query) < 20 and any('\u4e00' <= c <= '\u9fff' for c in query)
                
                if use_like:
                    # 使用LIKE搜索（中文）
                    query_sql = f"""
                        SELECT 
                            v.id as video_id,
                            v.title as video_title,
                            v.source_type,
                            v.duration_seconds,
                            v.file_path,
                            v.created_at,
                            (
                                SELECT fts_inner.source_field
                                FROM fts_content fts_inner
                                WHERE fts_inner.video_id = v.id
                                AND fts_inner.content LIKE ?
                                {field_filter.replace('fts.', 'fts_inner.')}
                                LIMIT 1
                            ) as source_field,
                            (
                                SELECT fts_inner.content
                                FROM fts_content fts_inner
                                WHERE fts_inner.video_id = v.id
                                AND fts_inner.content LIKE ?
                                {field_filter.replace('fts.', 'fts_inner.')}
                                LIMIT 1
                            ) as full_content,
                            0 as rank,
                            (
                                SELECT GROUP_CONCAT(t2.name, ', ')
                                FROM video_tags vt2
                                JOIN tags t2 ON vt2.tag_id = t2.id
                                WHERE vt2.video_id = v.id
                            ) as tags
                        FROM videos v
                        WHERE v.id IN (
                            SELECT DISTINCT fts_filter.video_id
                            FROM fts_content fts_filter
                            WHERE fts_filter.content LIKE ?
                            {field_filter.replace('fts.', 'fts_filter.')}
                        )
                        {tag_filter}
                        {order_clause.replace('fts.rank', 'rank').replace('ORDER BY rank', 'ORDER BY v.created_at DESC')}
                        LIMIT ? OFFSET ?
                    """
                else:
                    # 使用FTS搜索（英文/数字）
                    query_sql = f"""
                        SELECT 
                            v.id as video_id,
                            v.title as video_title,
                            v.source_type,
                            v.duration_seconds,
                            v.file_path,
                            v.created_at,
                            (
                                SELECT fts_inner.source_field
                                FROM fts_content fts_inner
                                WHERE fts_inner.video_id = v.id
                                AND fts_inner.content MATCH ?
                                {field_filter.replace('fts.', 'fts_inner.')}
                                ORDER BY fts_inner.rank
                                LIMIT 1
                            ) as source_field,
                            (
                                SELECT fts_inner.content
                                FROM fts_content fts_inner
                                WHERE fts_inner.video_id = v.id
                                AND fts_inner.content MATCH ?
                                {field_filter.replace('fts.', 'fts_inner.')}
                                ORDER BY fts_inner.rank
                                LIMIT 1
                            ) as full_content,
                            (
                                SELECT MIN(fts_inner.rank)
                                FROM fts_content fts_inner
                                WHERE fts_inner.video_id = v.id
                                AND fts_inner.content MATCH ?
                                {field_filter.replace('fts.', 'fts_inner.')}
                            ) as rank,
                            (
                                SELECT GROUP_CONCAT(t2.name, ', ')
                                FROM video_tags vt2
                                JOIN tags t2 ON vt2.tag_id = t2.id
                                WHERE vt2.video_id = v.id
                            ) as tags
                        FROM videos v
                        WHERE v.id IN (
                            SELECT DISTINCT fts_filter.video_id
                            FROM fts_content fts_filter
                            WHERE fts_filter.content MATCH ?
                            {field_filter.replace('fts.', 'fts_filter.')}
                        )
                        {tag_filter}
                        {order_clause.replace('fts.rank', 'rank')}
                        LIMIT ? OFFSET ?
                    """
            else:
                # 默认：显示所有匹配的内容片段
                query_sql = f"""
                    SELECT 
                        v.id as video_id,
                        v.title as video_title,
                        v.source_type,
                        v.duration_seconds,
                        v.file_path,
                        v.created_at,
                        fts.source_field,
                        fts.content as full_content,
                        fts.rank,
                        GROUP_CONCAT(t.name, ', ') as tags
                    FROM fts_content fts
                    JOIN videos v ON fts.video_id = v.id
                    LEFT JOIN video_tags vt ON v.id = vt.video_id
                    LEFT JOIN tags t ON vt.tag_id = t.id
                    WHERE fts.content MATCH ?
                    {field_filter}
                    {tag_filter}
                    GROUP BY v.id, fts.source_field, fts.content, fts.rank
                    {order_clause}
                    LIMIT ? OFFSET ?
                """
            
            # 执行查询
            # 检测是否包含中文
            use_like = len(query) < 20 and any('\u4e00' <= c <= '\u9fff' for c in query)
            
            if group_by_video:
                if use_like:
                    # LIKE模式：需要3个参数（source_field, content, WHERE过滤）
                    like_pattern = f'%{query}%'
                    params = [like_pattern, like_pattern, like_pattern]
                else:
                    # FTS模式：需要4个参数
                    params = [query, query, query, query]
            else:
                params = [query]
                
            if tags:
                params.extend(tags)
            params.extend([limit, offset])
            
            cursor = conn.execute(query_sql, params)
            rows = cursor.fetchall()
            
            # 转换为 SearchResult
            results = []
            for row in rows:
                # 提取匹配片段
                matched_snippet = self._extract_snippet(row['full_content'], query)
                
                # 计算相关性分数（BM25 rank 转换为 0-1）
                relevance_score = self._normalize_rank(row['rank'])
                
                if relevance_score < min_relevance:
                    continue
                
                # 获取时间戳信息（如果是 OCR 或 transcript）
                timestamp_info = self._get_timestamp_info(
                    row['video_id'], 
                    row['source_field'],
                    matched_snippet,
                    conn
                )
                
                result = SearchResult(
                    video_id=row['video_id'],
                    video_title=row['video_title'],
                    source_field=row['source_field'],
                    matched_snippet=matched_snippet,
                    full_content=row['full_content'] if len(row['full_content']) < 500 else None,
                    timestamp_seconds=timestamp_info.get('timestamp'),
                    timestamp_range=timestamp_info.get('range'),
                    tags=row['tags'].split(', ') if row['tags'] else [],
                    source_type=row['source_type'],
                    duration_seconds=row['duration_seconds'],
                    file_path=row['file_path'],
                    rank=row['rank'],
                    relevance_score=relevance_score,
                    created_at=row['created_at']
                )
                
                results.append(result)
            
            return results
            
        finally:
            conn.close()
    
    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        按标签搜索视频
        
        Args:
            tags: 标签列表
            match_all: True=AND逻辑（包含所有标签），False=OR逻辑（包含任一标签）
            limit: 返回结果数量
            offset: 分页偏移
        
        Returns:
            List[Dict]: 视频列表
        """
        conn = get_connection(self.db_path)
        
        try:
            if match_all:
                # AND逻辑：必须包含所有标签
                tag_placeholders = ','.join(['?'] * len(tags))
                query = f"""
                    SELECT 
                        v.*,
                        GROUP_CONCAT(t.name, ', ') as tags
                    FROM videos v
                    JOIN video_tags vt ON v.id = vt.video_id
                    JOIN tags t ON vt.tag_id = t.id
                    WHERE v.id IN (
                        SELECT vt2.video_id FROM video_tags vt2
                        JOIN tags t2 ON vt2.tag_id = t2.id
                        WHERE t2.name IN ({tag_placeholders})
                        GROUP BY vt2.video_id
                        HAVING COUNT(DISTINCT t2.id) = ?
                    )
                    GROUP BY v.id
                    ORDER BY v.created_at DESC
                    LIMIT ? OFFSET ?
                """
                params = [*tags, len(tags), limit, offset]
            else:
                # OR逻辑：包含任一标签
                tag_placeholders = ','.join(['?'] * len(tags))
                query = f"""
                    SELECT 
                        v.*,
                        GROUP_CONCAT(t.name, ', ') as tags,
                        COUNT(vt.tag_id) as matched_tag_count
                    FROM videos v
                    JOIN video_tags vt ON v.id = vt.video_id
                    JOIN tags t ON vt.tag_id = t.id
                    WHERE t.name IN ({tag_placeholders})
                    GROUP BY v.id
                    ORDER BY matched_tag_count DESC, v.created_at DESC
                    LIMIT ? OFFSET ?
                """
                params = [*tags, limit, offset]
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    def search_topics(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        搜索主题/章节
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            offset: 分页偏移
        
        Returns:
            List[Dict]: 主题列表（包含视频信息）
        """
        conn = get_connection(self.db_path)
        
        try:
            # 在主题标题和摘要中搜索
            cursor = conn.execute("""
                SELECT 
                    t.*,
                    v.title as video_title,
                    v.source_type,
                    v.file_path,
                    GROUP_CONCAT(tg.name, ', ') as video_tags
                FROM topics t
                JOIN videos v ON t.video_id = v.id
                LEFT JOIN video_tags vt ON v.id = vt.video_id
                LEFT JOIN tags tg ON vt.tag_id = tg.id
                WHERE t.title LIKE ? OR t.summary LIKE ?
                GROUP BY t.id
                ORDER BY t.video_id, t.sequence
                LIMIT ? OFFSET ?
            """, (f'%{query}%', f'%{query}%', limit, offset))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门标签"""
        conn = get_connection(self.db_path)
        
        try:
            cursor = conn.execute("""
                SELECT 
                    t.id,
                    t.name,
                    t.category,
                    t.count,
                    COUNT(DISTINCT vt.video_id) as video_count
                FROM tags t
                LEFT JOIN video_tags vt ON t.id = vt.tag_id
                GROUP BY t.id
                HAVING video_count > 0
                ORDER BY t.count DESC, video_count DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    def suggest_tags(self, prefix: str, limit: int = 10) -> List[str]:
        """标签自动补全"""
        conn = get_connection(self.db_path)
        
        try:
            cursor = conn.execute("""
                SELECT name FROM tags
                WHERE name LIKE ?
                ORDER BY count DESC
                LIMIT ?
            """, (f'{prefix}%', limit))
            
            return [row['name'] for row in cursor.fetchall()]
            
        finally:
            conn.close()
    
    # 辅助方法
    def _extract_snippet(self, content: str, query: str, context_chars: int = 150) -> str:
        """
        提取匹配片段（高亮上下文）
        
        Args:
            content: 完整内容
            query: 查询词
            context_chars: 上下文字符数
        
        Returns:
            str: 片段（带省略号）
        """
        # 简单实现：查找查询词第一次出现的位置
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 处理 FTS5 查询语法（去除操作符）
        search_term = query_lower.split()[0] if query_lower else ''
        
        pos = content_lower.find(search_term)
        
        if pos == -1:
            # 未找到，返回开头
            return content[:context_chars * 2] + ('...' if len(content) > context_chars * 2 else '')
        
        # 提取上下文
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(search_term) + context_chars)
        
        snippet = content[start:end]
        
        # 添加省略号
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet = snippet + '...'
        
        return snippet
    
    def _normalize_rank(self, rank: float) -> float:
        """
        将 BM25 rank 归一化到 0-1
        
        FTS5 的 rank 是负数，越小越好
        """
        # 简单的线性映射（可以根据实际分布调整）
        # rank 通常在 -50 到 -0.1 之间
        normalized = max(0.0, min(1.0, 1.0 + (rank / 50.0)))
        return round(normalized, 3)
    
    def _get_timestamp_info(
        self, 
        video_id: int, 
        source_field: str, 
        snippet: str,
        conn
    ) -> Dict[str, Any]:
        """
        获取匹配片段的时间戳信息
        
        Returns:
            {'timestamp': float, 'range': (start, end)}
        """
        result = {}
        
        # 仅对 transcript 和 ocr 查询时间线
        if source_field not in ['transcript', 'ocr']:
            return result
        
        try:
            # 在时间线表中查找匹配文本
            if source_field == 'transcript':
                cursor = conn.execute("""
                    SELECT timestamp_seconds 
                    FROM timeline_entries
                    WHERE video_id = ? AND transcript_text LIKE ?
                    ORDER BY timestamp_seconds
                    LIMIT 1
                """, (video_id, f'%{snippet[:50]}%'))
            else:  # ocr
                cursor = conn.execute("""
                    SELECT timestamp_seconds 
                    FROM timeline_entries
                    WHERE video_id = ? AND ocr_text LIKE ?
                    ORDER BY timestamp_seconds
                    LIMIT 1
                """, (video_id, f'%{snippet[:50]}%'))
            
            row = cursor.fetchone()
            if row:
                result['timestamp'] = row['timestamp_seconds']
                # 假设片段持续约 5 秒
                result['range'] = (row['timestamp_seconds'], row['timestamp_seconds'] + 5.0)
        
        except Exception:
            pass
        
        return result
