"""平台特定配置模块"""

from archiver.platforms.base import PlatformAdapter
from archiver.platforms.zhihu import ZhihuAdapter
from archiver.platforms.xiaohongshu import XiaohongshuAdapter
from archiver.platforms.bilibili import BilibiliAdapter
from archiver.platforms.reddit import RedditAdapter
from archiver.platforms.twitter import TwitterAdapter
from archiver.platforms.wordpress import WordPressAdapter

__all__ = [
    "PlatformAdapter",
    "ZhihuAdapter",
    "XiaohongshuAdapter",
    "BilibiliAdapter",
    "RedditAdapter",
    "TwitterAdapter",
    "WordPressAdapter",
]
