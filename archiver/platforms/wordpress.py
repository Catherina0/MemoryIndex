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
            content_selector=".available-content, .gh-content, .prose, .single-post, article, .entry-content, .post-body, .article-content, .post-content, .blog-post, #content, [role='main'], main",
            exclude_selector="#comments, .comments, .sidebar, .footer, .ad, .advertisement, .share-buttons, .related-posts, .subscription-widget, .newsletter-form, .cookie-banner, .modal, .popup",
            wait_for_selector=".available-content, article, .entry-content, main",
            requires_login=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理通用URL
        """
        return url
