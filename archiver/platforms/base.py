"""
平台适配器基类
定义所有平台适配器的通用接口
"""

from typing import Optional, List
from dataclasses import dataclass


@dataclass
class PlatformConfig:
    """平台配置"""
    name: str
    content_selector: str
    exclude_selector: Optional[str] = None
    wait_for_selector: Optional[str] = None
    requires_login: bool = False
    user_agent: Optional[str] = None


class PlatformAdapter:
    """平台适配器基类"""
    
    def __init__(self, config: Optional[PlatformConfig] = None):
        """
        初始化平台适配器
        
        Args:
            config: 平台配置
        """
        if config is None:
            config = self.get_default_config()
        self.config = config
    
    @property
    def name(self) -> str:
        """平台名称"""
        return self.config.name
    
    @property
    def content_selector(self) -> str:
        """正文内容CSS选择器"""
        return self.config.content_selector
    
    @property
    def exclude_selector(self) -> Optional[str]:
        """需要排除的内容CSS选择器"""
        return self.config.exclude_selector
    
    @property
    def wait_for_selector(self) -> Optional[str]:
        """等待加载的CSS选择器"""
        return self.config.wait_for_selector
    
    @property
    def requires_login(self) -> bool:
        """是否需要登录"""
        return self.config.requires_login
    
    @property
    def user_agent(self) -> Optional[str]:
        """自定义User-Agent"""
        return self.config.user_agent
    
    def get_default_config(self) -> PlatformConfig:
        """
        获取默认配置（子类必须实现）
        
        Returns:
            平台配置
        """
        raise NotImplementedError("Subclasses must implement get_default_config()")
    
    def extract_metadata(self, html: str) -> dict:
        """
        从HTML中提取元数据（可选实现）
        
        Args:
            html: HTML内容
        
        Returns:
            元数据字典
        """
        return {}
    
    def preprocess_url(self, url: str) -> str:
        """
        预处理URL（可选实现）
        
        Args:
            url: 原始URL
        
        Returns:
            处理后的URL
        """
        return url
