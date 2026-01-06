"""
URL解析器
用于检测URL所属的平台
"""

import re
from urllib.parse import urlparse


def detect_platform(url: str) -> str:
    """
    检测URL所属的平台
    
    Args:
        url: 目标URL
    
    Returns:
        平台名称字符串
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # 知乎
    if 'zhihu.com' in domain:
        return 'zhihu'
    
    # 小红书
    if 'xiaohongshu.com' in domain or 'xhslink.com' in domain:
        return 'xiaohongshu'
    
    # B站
    if 'bilibili.com' in domain or 'b23.tv' in domain:
        return 'bilibili'
    
    # Reddit
    if 'reddit.com' in domain:
        return 'reddit'
    
    # 默认使用WordPress/通用适配器
    return 'wordpress'


def normalize_url(url: str) -> str:
    """
    标准化URL格式
    
    Args:
        url: 原始URL
    
    Returns:
        标准化后的URL
    """
    # 确保URL有协议
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # 移除URL末尾的斜杠
    url = url.rstrip('/')
    
    return url


def extract_domain(url: str) -> str:
    """
    从URL中提取域名
    
    Args:
        url: 目标URL
    
    Returns:
        域名字符串
    """
    parsed = urlparse(url)
    return parsed.netloc


def is_valid_url(url: str) -> bool:
    """
    检查URL是否有效
    
    Args:
        url: 待检查的URL
    
    Returns:
        是否有效
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
