"""
数据库层模块
提供数据存储、检索和搜索功能
"""

from .schema import init_database
from .repository import VideoRepository
from .search import SearchRepository
from .models import Video, Artifact, Tag, Topic
from .whoosh_search import WhooshSearchIndex, get_whoosh_index, check_whoosh_status

__all__ = [
    'init_database',
    'VideoRepository',
    'SearchRepository',
    'Video',
    'Artifact',
    'Tag',
    'Topic',
    'WhooshSearchIndex',
    'get_whoosh_index',
    'check_whoosh_status',
]
