"""
搜索 API
提供全文搜索、标签搜索、主题搜索等功能
支持 FTS5（英文）和 Whoosh+jieba（中文）混合搜索
"""
from typing import Optional, List, Dict, Any
from enum import Enum

from .schema import get_connection
from .models import SearchResult

# 尝试导入 Whoosh 搜索
try:
    from .whoosh_search import get_whoosh_index, check_whoosh_status
    WHOOSH_AVAILABLE = check_whoosh_status()['ready']
except ImportError:
    WHOOSH_AVAILABLE = False


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
    
    def _escape_fts_query(self, query: str) -> str:
        """
        转义FTS查询中的特殊字符
        
        Args:
            query: 原始查询字符串
            
        Returns:
            转义后的查询字符串
        """
        # FTS5中的特殊字符需要用双引号包围而不是转义
        # 因为反斜杠转义在某些情况下会导致语法错误
        special_chars = '-"*()[]{}~^|&'
        if any(char in query for char in special_chars):
            # 如果包含特殊字符，用双引号包围（但要先转义内部的双引号）
            escaped_query = query.replace('"', '""')
            return f'"{escaped_query}"'
        return query
    
    def _get_fuzzy_variants(self, query: str) -> List[str]:
        """
        生成模糊搜索的变体查询
        
        Args:
            query: 原始查询
            
        Returns:
            模糊搜索变体列表
        """
        variants = []
        
        # 基本通配符搜索
        variants.append(f"{query}*")
        
        # MBTI类型特殊处理
        mbti_types = ['infp', 'infj', 'intp', 'intj', 'enfp', 'enfj', 'entp', 'entj', 
                      'isfp', 'isfj', 'istp', 'istj', 'esfp', 'esfj', 'estp', 'estj']
        query_lower = query.lower()
        
        if query_lower in mbti_types:
            # 为MBTI类型添加相关的变体
            if query_lower.startswith('in'):  # 内向类型
                variants.extend(['in*', 'inf*', 'int*'])
                if 'f' in query_lower:  # 感情型
                    variants.extend(['*nf*', 'f*'])
                if 't' in query_lower:  # 思维型
                    variants.extend(['*nt*', 't*'])
                if 'p' in query_lower:  # 感知型
                    variants.extend(['*p*'])
                if 'j' in query_lower:  # 判断型
                    variants.extend(['*j*'])
            elif query_lower.startswith('en'):  # 外向类型
                variants.extend(['en*', 'enf*', 'ent*'])
                # 类似的逻辑...
        
        # 对于短查询，生成更多变体（非MBTI类型）
        if len(query) >= 3 and len(query) <= 8 and query.isalpha() and query_lower not in mbti_types:
            # 添加中间通配符（处理插入错误）
            for i in range(1, len(query)):
                variant = query[:i] + '*' + query[i:]
                variants.append(variant)
            
            # 添加部分匹配（处理删除错误）
            for i in range(len(query)):
                if i == 0:
                    variant = query[1:] + '*'
                elif i == len(query) - 1:
                    variant = query[:-1] + '*'
                else:
                    variant = query[:i] + query[i+1:] + '*'
                
                # 确保变体足够长，避免太短的匹配
                if len(variant.rstrip('*')) >= 2:
                    variants.append(variant)
        
        # 清理变体：去重
        return list(set(variants))
    
    def search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        fields: SearchField = SearchField.ALL,
        limit: int = 20,
        offset: int = 0,
        sort_by: SortBy = SortBy.RELEVANCE,
        min_relevance: float = 0.0,
        group_by_video: bool = True,
        match_all_keywords: bool = False,
        fuzzy: bool = True  # 默认启用模糊搜索
    ) -> List[SearchResult]:
        """
        全文搜索
        
        Args:
            query: 搜索查询字符串（支持多关键词，用空格分隔）
            tags: 标签过滤（AND逻辑：必须包含所有标签）
            fields: 搜索字段范围
            limit: 返回结果数量
            offset: 分页偏移
            sort_by: 排序方式
            min_relevance: 最小相关性分数（0-1）
            group_by_video: 是否按视频聚合（默认True，每个视频只显示最佳匹配）
            match_all_keywords: 多关键词逻辑（True=AND都匹配，False=OR任一匹配）
            fuzzy: 是否启用模糊搜索（支持部分匹配）
        
        Returns:
            List[SearchResult]: 搜索结果列表
        """
        # 解析多关键词
        keywords = [k.strip() for k in query.split() if k.strip()]
        if not keywords:
            return []
        
        # 单关键词：使用原有逻辑
        if len(keywords) == 1:
            return self._search_single(
                keywords[0], tags, fields, limit, offset, 
                sort_by, min_relevance, group_by_video, fuzzy
            )
        
        # 多关键词：收集所有结果并计算综合相似度
        all_results = {}  # {video_id: {result, scores: [score1, score2, ...], matched_count}}
        
        for keyword in keywords:
            results = self._search_single(
                keyword, tags, fields, 999, 0,  # 大limit确保找到所有
                sort_by, 0, group_by_video, fuzzy  # min_relevance=0，后续统一过滤
            )
            for r in results:
                if r.video_id not in all_results:
                    all_results[r.video_id] = {
                        'result': r,
                        'scores': [],
                        'matched_count': 0
                    }
                all_results[r.video_id]['scores'].append(r.relevance_score or 0.5)
                all_results[r.video_id]['matched_count'] += 1
        
        # 计算综合相似度
        final_results = []
        for video_id, data in all_results.items():
            if match_all_keywords and data['matched_count'] < len(keywords):
                # AND逻辑：必须匹配所有关键词
                continue
            
            # 综合相似度 = 平均分 * (匹配关键词数 / 总关键词数)
            avg_score = sum(data['scores']) / len(data['scores'])
            coverage = data['matched_count'] / len(keywords)
            combined_score = avg_score * (0.7 + 0.3 * coverage)  # 70%看质量，30%看覆盖率
            
            # 更新结果的相似度
            result = data['result']
            result.relevance_score = round(combined_score, 3)
            
            if combined_score >= min_relevance:
                final_results.append(result)
        
        # 按相似度排序
        if sort_by == SortBy.RELEVANCE:
            final_results.sort(key=lambda x: x.relevance_score or 0, reverse=True)
        elif sort_by == SortBy.DATE:
            final_results.sort(key=lambda x: x.created_at or '', reverse=True)
        
        # 应用分页
        return final_results[offset:offset+limit]
    
    def _search_single(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        fields: SearchField = SearchField.ALL,
        limit: int = 20,
        offset: int = 0,
        sort_by: SortBy = SortBy.RELEVANCE,
        min_relevance: float = 0.0,
        group_by_video: bool = True,
        fuzzy: bool = True  # 默认启用模糊搜索
    ) -> List[SearchResult]:
        """
        单关键词搜索的内部实现
        
        Args:
            fuzzy: 是否启用模糊搜索（中文用LIKE %x%，英文用FTS通配符）
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
            
            # 模糊搜索预处理
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)
            original_query = query  # 保存原始查询
            fuzzy_queries = []  # 模糊搜索的查询变体
            
            # 如果是中文且 Whoosh 可用，优先使用 Whoosh 搜索
            if has_chinese and WHOOSH_AVAILABLE:
                whoosh_results = self._search_with_whoosh(
                    query=original_query,
                    tags=tags,
                    limit=limit,
                    offset=offset,
                    min_relevance=min_relevance,
                    conn=conn
                )
                if whoosh_results is not None:
                    return whoosh_results
                # Whoosh 搜索失败，回退到 LIKE
            
            if fuzzy and not has_chinese:
                # 英文模糊搜索：生成多种变体以处理拼写错误
                fuzzy_queries = self._get_fuzzy_variants(query)
                # 使用第一个变体作为主查询
                if fuzzy_queries:
                    query = fuzzy_queries[0]
                else:
                    query = self._escape_fts_query(query) + '*'
            
            # 决定使用LIKE还是FTS搜索
            # 中文短查询或者明确要求模糊搜索时使用LIKE，英文模糊搜索使用FTS
            use_like = fuzzy and has_chinese and len(original_query) < 20
            
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
            
            # 执行查询（支持模糊搜索多变体合并）
            all_rows = []
            used_video_ids = set()  # 避免重复的视频
            
            # 如果是英文模糊搜索且有多个变体，合并所有变体的结果
            if fuzzy and not has_chinese and not use_like and fuzzy_queries:
                # 对变体按照重要性排序：原查询通配符 > 前缀匹配 > 其他变体
                prioritized_queries = []
                exact_match = f"{original_query}*"
                prefix_patterns = [q for q in fuzzy_queries if q.endswith('*') and '*' not in q[:-1]]
                other_patterns = [q for q in fuzzy_queries if q not in prefix_patterns and q != exact_match]
                
                if exact_match in fuzzy_queries:
                    prioritized_queries.append(exact_match)
                prioritized_queries.extend(sorted(prefix_patterns, key=len, reverse=True))  # 长的前缀优先
                prioritized_queries.extend(other_patterns)
                
                for attempt_query in prioritized_queries:
                    try:
                        if group_by_video:
                            # FTS模式：需要4个参数
                            params = [attempt_query, attempt_query, attempt_query, attempt_query]
                        else:
                            params = [attempt_query]
                            
                        if tags:
                            params.extend(tags)
                        params.extend([limit * 2, offset])  # 适当增加limit
                        
                        cursor = conn.execute(query_sql, params)
                        variant_rows = cursor.fetchall()
                        
                        # 合并结果，避免重复视频，并记录匹配的变体
                        for row in variant_rows:
                            if group_by_video:
                                video_id = row['video_id']
                                if video_id not in used_video_ids:
                                    used_video_ids.add(video_id)
                                    # 添加变体匹配信息
                                    row_dict = dict(row)
                                    row_dict['matched_variant'] = attempt_query
                                    row_dict['variant_priority'] = prioritized_queries.index(attempt_query)
                                    all_rows.append(row_dict)
                                    # 如果已经收集到足够的结果就可以停止某些变体
                                    if len(all_rows) >= limit * 1.5:
                                        break
                            else:
                                row_dict = dict(row)
                                row_dict['matched_variant'] = attempt_query
                                row_dict['variant_priority'] = prioritized_queries.index(attempt_query)
                                all_rows.append(row_dict)
                                
                    except Exception as e:
                        # 如果查询失败，尝试下一个变体
                        continue
                
                # 按相关性排序并限制结果数量
                if all_rows and sort_by == SortBy.RELEVANCE:
                    all_rows.sort(key=lambda x: x['rank'] if 'rank' in x.keys() and x['rank'] is not None else 999)
                rows = all_rows[:limit]
                
                # 使用原始查询进行片段提取
                query = original_query
            else:
                # 标准查询执行
                if group_by_video:
                    if use_like:
                        # LIKE模式：需要3个参数（source_field, content, WHERE过滤）
                        like_pattern = f'%{original_query}%'
                        params = [like_pattern, like_pattern, like_pattern]
                    else:
                        # FTS模式：需要4个参数（使用处理过的query，可能包含通配符）
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
                if isinstance(row, dict) and 'matched_variant' in row:
                    # 多变体搜索的结果
                    matched_snippet = self._extract_snippet(row['full_content'], original_query)
                    # 计算基于变体匹配的相关性分数
                    relevance_score = self._calculate_variant_relevance(
                        row['rank'], 
                        row['matched_variant'], 
                        original_query,
                        row['variant_priority']
                    )
                else:
                    # 标准搜索的结果
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
    
    def _search_with_whoosh(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        min_relevance: float = 0.0,
        conn = None
    ) -> Optional[List[SearchResult]]:
        """
        使用 Whoosh 进行中文全文搜索（按视频聚合，每个视频只返回最相关的结果）
        
        Args:
            query: 搜索查询（中文）
            tags: 标签过滤
            limit: 返回结果数量
            offset: 分页偏移
            min_relevance: 最小相关性阈值
            conn: 数据库连接
        
        Returns:
            List[SearchResult] 或 None（如果 Whoosh 搜索失败）
        """
        try:
            whoosh_index = get_whoosh_index(self.db_path)
            
            # 使用 Whoosh 搜索（获取更多结果用于聚合）
            whoosh_results = whoosh_index.search(
                query, 
                limit=(limit + offset) * 5  # 获取更多结果以便聚合
            )
            
            if not whoosh_results:
                return []
            
            # 按视频ID聚合，保留每个视频最相关的结果
            video_best_results = {}  # video_id -> (relevance_score, wr, video_row)
            
            for wr in whoosh_results:
                video_id = wr.video_id
                relevance_score = wr.relevance_score if wr.relevance_score else 0.5
                
                # 检查是否已有该视频的结果，保留相关性更高的
                if video_id in video_best_results:
                    if relevance_score <= video_best_results[video_id][0]:
                        continue  # 已有更相关的结果，跳过
                
                # 检查标签
                if tags and video_id:
                    cursor = conn.execute("""
                        SELECT COUNT(DISTINCT t.id) as tag_count
                        FROM video_tags vt
                        JOIN tags t ON vt.tag_id = t.id
                        WHERE vt.video_id = ? AND t.name IN ({})
                    """.format(','.join(['?'] * len(tags))), [video_id] + tags)
                    row = cursor.fetchone()
                    if row['tag_count'] < len(tags):
                        continue  # 不满足所有标签要求
                
                # 获取完整视频信息
                cursor = conn.execute("""
                    SELECT 
                        v.id, v.title, v.source_type, 
                        v.duration_seconds, v.file_path, v.created_at,
                        (
                            SELECT GROUP_CONCAT(t.name, ', ')
                            FROM video_tags vt
                            JOIN tags t ON vt.tag_id = t.id
                            WHERE vt.video_id = v.id
                        ) as tags
                    FROM videos v
                    WHERE v.id = ?
                """, [video_id])
                video_row = cursor.fetchone()
                
                if not video_row:
                    continue
                
                if relevance_score < min_relevance:
                    continue
                
                # 保存/更新该视频的最佳结果
                video_best_results[video_id] = (relevance_score, wr, video_row)
            
            # 构建聚合后的结果列表
            filtered_results = []
            for video_id, (relevance_score, wr, video_row) in video_best_results.items():
                # 提取匹配片段
                content = wr.content or ''
                matched_snippet = self._extract_snippet(content, query)
                source_field = wr.source or 'ocr_text'
                
                # 获取时间戳信息
                timestamp_info = self._get_timestamp_info(
                    video_id, 
                    source_field,
                    matched_snippet,
                    conn
                )
                
                result = SearchResult(
                    video_id=video_id,
                    video_title=video_row['title'],
                    source_field=source_field,
                    matched_snippet=matched_snippet,
                    full_content=content if len(content) < 500 else None,
                    timestamp_seconds=timestamp_info.get('timestamp'),
                    timestamp_range=timestamp_info.get('range'),
                    tags=video_row['tags'].split(', ') if video_row['tags'] else [],
                    source_type=video_row['source_type'],
                    duration_seconds=video_row['duration_seconds'],
                    file_path=video_row['file_path'],
                    rank=None,  # Whoosh 不使用 rank
                    relevance_score=relevance_score,
                    created_at=video_row['created_at']
                )
                
                filtered_results.append(result)
            
            # 按相关性排序
            filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 应用分页
            return filtered_results[offset:offset + limit]
            
        except Exception as e:
            # Whoosh 搜索失败，返回 None 以触发回退
            import sys
            print(f"Whoosh 搜索失败: {e}", file=sys.stderr)
            return None
    
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
    
    def _calculate_variant_relevance(self, rank: float, matched_variant: str, original_query: str, variant_priority: int) -> float:
        """
        计算基于变体匹配的相关性分数
        
        Args:
            rank: FTS BM25 rank分数
            matched_variant: 匹配到的查询变体
            original_query: 原始查询
            variant_priority: 变体优先级（0最高）
            
        Returns:
            调整后的相关性分数
        """
        # 基础BM25分数
        base_score = self._normalize_rank(rank)
        
        # 变体权重调整
        variant_weight = 1.0
        
        # 精确匹配奖励
        if matched_variant == f"{original_query}*":
            variant_weight = 1.0  # 最高权重
        elif matched_variant == original_query:
            variant_weight = 1.0  # 完全精确匹配
        else:
            # 根据变体优先级和类型调整权重
            if variant_priority == 0:
                variant_weight = 1.0
            elif variant_priority <= 2:
                variant_weight = 0.85  # 高优先级变体
            elif variant_priority <= 5:
                variant_weight = 0.7   # 中等优先级
            else:
                variant_weight = 0.6   # 低优先级变体
            
            # 特殊情况：如果是MBTI相关的智能匹配
            original_lower = original_query.lower()
            variant_lower = matched_variant.lower().replace('*', '')
            
            if original_lower in ['infp', 'infj', 'intp', 'intj', 'enfp', 'enfj', 'entp', 'entj', 
                                 'isfp', 'isfj', 'istp', 'istj', 'esfp', 'esfj', 'estp', 'estj']:
                # MBTI智能匹配权重调整
                if variant_lower in ['inf', 'int', 'enf', 'ent', 'isf', 'ist', 'esf', 'est']:
                    # 检查是否是同系列（如INFP -> INF系列）
                    if original_lower.startswith(variant_lower):
                        variant_weight = 0.9  # 同系列匹配
                    else:
                        variant_weight = 0.75  # 跨系列匹配
                elif variant_lower in ['in', 'en', 'is', 'es']:
                    variant_weight = 0.65  # MBTI大类匹配
                elif variant_lower in ['f', 't', 'p', 'j']:
                    variant_weight = 0.5   # MBTI维度匹配
        
        # 内容相关性检查（简单的关键词匹配）
        content_bonus = 1.0
        # 这里可以添加更复杂的内容相关性分析
        
        final_score = base_score * variant_weight * content_bonus
        return round(min(1.0, final_score), 3)

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
