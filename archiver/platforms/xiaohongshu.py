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
            content_selector=".note-content, #detail-desc, .note-text",
            exclude_selector=".comments-container, .interaction-container, .footer",
            wait_for_selector=".note-content",
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
