"""
推特(Twitter/X)平台适配器
"""

from archiver.platforms.base import PlatformAdapter, PlatformConfig


class TwitterAdapter(PlatformAdapter):
    """推特(Twitter/X)平台适配器"""
    
    def get_default_config(self) -> PlatformConfig:
        """获取推特的默认配置"""
        return PlatformConfig(
            name="twitter",
            # 推特的主要内容选择器
            # article[data-testid="tweet"] 是单条推文
            # [data-testid="tweetText"] 是推文文本
            content_selector="article[data-testid='tweet']",
            exclude_selector=(
                "[data-testid='sidebarColumn'], "
                "[aria-label*='Timeline'], "
                "[data-testid='TopNavBar'], "
                "[role='navigation'], "
                "[data-testid='DMDrawer'], "
                "aside, nav, "
                # 排除推文底部的统计数据（阅读量等）
                "[aria-label*='View post analytics'], "
                # 排除操作栏（回复、转推、点赞等）
                "[role='group']"
            ),
            wait_for_selector="[data-testid='tweetText']",
            requires_login=True,  # 推特通常需要登录才能查看完整内容
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理推特URL
        """
        # 统一转换为 twitter.com (即使用户使用 x.com)
        url = url.replace('x.com', 'twitter.com')
        
        # 移除 URL 参数（保留主要路径）
        if '?' in url:
            base_url = url.split('?')[0]
            # 但保留推文ID
            return base_url
        
        return url
