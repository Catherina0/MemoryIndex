"""
Reddit平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class RedditAdapter(PlatformAdapter):
    """Reddit平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取Reddit的默认配置"""
        return PlatformConfig(
            name="reddit",
            content_selector="shreddit-post, .Post, [slot='post-media-container']",
            exclude_selector="shreddit-comment-tree, .comment, .promotedlink",
            wait_for_selector="shreddit-post",
            requires_login=False,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理Reddit URL
        确保使用old.reddit.com以获得更好的抓取效果
        """
        # 可选：转换为old.reddit.com
        # url = url.replace('www.reddit.com', 'old.reddit.com')
        return url
