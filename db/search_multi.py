"""
多关键词搜索扩展
"""
from typing import List

def parse_keywords(query: str) -> List[str]:
    """解析搜索查询为关键词列表"""
    return [k.strip() for k in query.split() if k.strip()]

def is_chinese_keywords(keywords: List[str]) -> bool:
    """判断是否所有关键词都是短中文词（适合LIKE搜索）"""
    return all(len(k) < 20 and any('\u4e00' <= c <= '\u9fff' for c in k) for k in keywords)

def build_like_conditions(keywords: List[str], match_all: bool, field_prefix: str = "fts_inner") -> str:
    """构建LIKE条件"""
    if match_all:
        # AND逻辑
        return " AND ".join([f"{field_prefix}.content LIKE ?" for _ in keywords])
    else:
        # OR逻辑
        return " OR ".join([f"{field_prefix}.content LIKE ?" for _ in keywords])

def build_fts_query(keywords: List[str], match_all: bool) -> str:
    """构建FTS查询字符串"""
    if match_all:
        return " AND ".join(keywords)
    else:
        return " OR ".join(keywords)

def build_like_params(keywords: List[str], num_usages: int) -> List[str]:
    """构建LIKE查询参数列表"""
    like_patterns = [f'%{k}%' for k in keywords]
    return like_patterns * num_usages
