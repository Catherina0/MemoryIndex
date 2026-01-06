"""
URL解析器
用于检测URL所属的平台
"""

import re
from urllib.parse import urlparse
from typing import Optional


def extract_url_from_text(text: str) -> Optional[str]:
    """
    从文本中提取URL（支持从分享文本中自动提取）
    
    支持的场景：
    - 纯URL输入
    - URL + 其他文本（自动提取URL）
    - 多个URL（返回第一个有效的）
    
    Args:
        text: 输入文本（可能包含URL和其他内容）
        
    Returns:
        提取到的URL，或None
    
    示例：
        >>> extract_url_from_text("57 【标题】 😆 https://www.xiaohongshu.com/item/123")
        'https://www.xiaohongshu.com/item/123'
    """
    text = text.strip()
    
    # 如果是纯URL，直接返回
    if is_valid_url(text):
        return text
    
    # 从文本中提取 URL（通用模式）
    url_pattern = r'https?://[^\s\"\'\u4e00-\u9fff]+'
    match = re.search(url_pattern, text)
    
    if match:
        url = match.group(0)
        # 移除可能的尾部标点
        url = url.rstrip('.,;!?')
        
        # 尝试修复常见的小红书 URL 格式错误（缺失问号）
        # Case: .../item/<id>source=...
        if 'xiaohongshu.com' in url and '/item/' in url and '?' not in url:
            # 检查是否有 source=, xhsshare= 等参数直接连在ID后面
            common_params = ['source=', 'xhsshare=', 'xsec_token=']
            for param in common_params:
                if param in url:
                    # 找到参数开始的位置
                    idx = url.find(param)
                    if idx > 0:
                        # 插入问号
                        fixed_url = url[:idx] + '?' + url[idx:]
                        print(f"🔧 自动修复URL格式: {url} -> {fixed_url}")
                        return fixed_url
                        
        return url
    
    return None


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
