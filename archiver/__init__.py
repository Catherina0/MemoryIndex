"""
网页归档模块 - Universal Web Archiver
支持从多个平台（知乎、小红书、B站等）精准提取正文并保存为 Markdown 格式
"""

__version__ = "0.1.0"

from archiver.core.crawler import UniversalArchiver
from archiver.utils.url_parser import detect_platform

__all__ = ["UniversalArchiver", "detect_platform"]
