"""
知乎平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class ZhihuAdapter(PlatformAdapter):
    """知乎平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取知乎的默认配置"""
        return PlatformConfig(
            name="zhihu",
            content_selector=".RichContent-inner, .QuestionAnswer-content, .Post-RichTextContainer",
            exclude_selector=".Comments-container, .ContentItem-actions, .Reward, .Card",
            wait_for_selector=".RichContent-inner",
            requires_login=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理知乎URL
        移除不必要的参数，确保是回答页面
        """
        # 移除URL参数
        if '?' in url:
            url = url.split('?')[0]
        return url
