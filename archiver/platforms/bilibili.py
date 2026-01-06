"""
B站平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class BilibiliAdapter(PlatformAdapter):
    """B站平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取B站的默认配置"""
        return PlatformConfig(
            name="bilibili",
            content_selector=".article-holder, #v_desc, .video-desc",
            exclude_selector=".comment-list, .rec-list, .ad-report",
            wait_for_selector=".article-holder, #v_desc",
            requires_login=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理B站URL
        """
        # 移除URL参数，保留BV号或av号
        if '?' in url:
            url = url.split('?')[0]
        return url
