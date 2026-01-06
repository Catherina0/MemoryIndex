"""
WordPress/通用平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class WordPressAdapter(PlatformAdapter):
    """WordPress/通用平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取通用配置"""
        return PlatformConfig(
            name="wordpress",
            content_selector="article, .entry-content, .post-body, .article-content, main",
            exclude_selector="#comments, .comments, .sidebar, .footer, .ad, .advertisement",
            wait_for_selector="article, .entry-content",
            requires_login=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理通用URL
        """
        return url
