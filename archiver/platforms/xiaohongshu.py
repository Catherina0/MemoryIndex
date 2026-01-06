"""
小红书平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class XiaohongshuAdapter(PlatformAdapter):
    """小红书平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取小红书的默认配置"""
        return PlatformConfig(
            name="xiaohongshu",
            # 小红书的内容选择器（优先级从高到低）
            # 优先使用 .note-container 以同时包含图片和文字
            content_selector="#noteContainer, .note-container, .note-detail, #detail-desc, .note-content",
            exclude_selector=".comments-container, .comment-container, .footer, [class*='comment'], [class*='related'], .recommend-container",
            wait_for_selector="#detail-desc",
            requires_login=True,  # 小红书通常需要登录
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理小红书URL
        """
        # 移除URL参数
        if '?' in url:
            url = url.split('?')[0]
        return url
