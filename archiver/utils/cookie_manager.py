"""
Cookie管理器
用于处理需要登录态的网站
"""

import json
import logging
from typing import Dict, Optional
from pathlib import Path

try:
    import browser_cookie3
    BROWSER_COOKIE3_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE3_AVAILABLE = False
    logging.warning("browser_cookie3 not installed. Run: pip install browser_cookie3")


logger = logging.getLogger(__name__)


class CookieManager:
    """Cookie管理器"""
    
    def __init__(self):
        """初始化Cookie管理器"""
        self.cookies_cache = {}
    
    def load_from_browser(
        self,
        domain: str,
        browser: str = 'chrome'
    ) -> Optional[Dict[str, str]]:
        """
        从浏览器加载Cookies
        
        Args:
            domain: 目标域名
            browser: 浏览器类型 (chrome, firefox, edge, safari)
        
        Returns:
            Cookie字典，失败返回None
        """
        if not BROWSER_COOKIE3_AVAILABLE:
            logger.error("browser_cookie3 not installed")
            return None
        
        # 检查缓存
        cache_key = f"{browser}:{domain}"
        if cache_key in self.cookies_cache:
            logger.info(f"Using cached cookies for {domain}")
            return self.cookies_cache[cache_key]
        
        try:
            # 根据浏览器类型加载
            if browser.lower() == 'chrome':
                cj = browser_cookie3.chrome(domain_name=domain)
            elif browser.lower() == 'firefox':
                cj = browser_cookie3.firefox(domain_name=domain)
            elif browser.lower() == 'edge':
                cj = browser_cookie3.edge(domain_name=domain)
            elif browser.lower() == 'safari':
                cj = browser_cookie3.safari(domain_name=domain)
            else:
                logger.error(f"Unsupported browser: {browser}")
                return None
            
            # 转换为字典
            cookies_dict = {cookie.name: cookie.value for cookie in cj}
            
            # 缓存
            self.cookies_cache[cache_key] = cookies_dict
            
            logger.info(f"Loaded {len(cookies_dict)} cookies for {domain} from {browser}")
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None
    
    def load_from_file(self, cookie_file: str) -> Optional[Dict[str, str]]:
        """
        从文件加载Cookies（Netscape格式）
        
        Args:
            cookie_file: Cookie文件路径
        
        Returns:
            Cookie字典，失败返回None
        """
        try:
            cookies_dict = {}
            with open(cookie_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # 跳过注释和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        name = parts[5]
                        value = parts[6]
                        cookies_dict[name] = value
            
            logger.info(f"Loaded {len(cookies_dict)} cookies from {cookie_file}")
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Failed to load cookies from file: {e}")
            return None
    
    def save_to_file(self, cookies: Dict[str, str], cookie_file: str) -> bool:
        """
        保存Cookies到文件
        
        Args:
            cookies: Cookie字典
            cookie_file: 保存路径
        
        Returns:
            是否成功
        """
        try:
            with open(cookie_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for name, value in cookies.items():
                    # 简化格式，只保存必要信息
                    f.write(f".example.com\tTRUE\t/\tFALSE\t0\t{name}\t{value}\n")
            
            logger.info(f"Saved {len(cookies)} cookies to {cookie_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    def clear_cache(self):
        """清除Cookie缓存"""
        self.cookies_cache.clear()
    
    def load_from_xhs_config(self) -> Optional[Dict[str, str]]:
        """
        从小红书下载器配置中加载Cookie（复用视频下载模块的配置）
        
        Returns:
            Cookie字典，失败返回None
        """
        try:
            # XHS-Downloader 配置文件路径
            config_path = Path(__file__).parent.parent.parent / "XHS-Downloader" / "Volume" / "settings.json"
            
            if not config_path.exists():
                logger.warning(f"XHS-Downloader config not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            cookie_str = config.get('cookie', '')
            if not cookie_str:
                logger.warning("No cookie found in XHS-Downloader config")
                return None
            
            # 将Cookie字符串转换为字典
            cookies_dict = {}
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies_dict[key.strip()] = value.strip()
            
            logger.info(f"Loaded {len(cookies_dict)} cookies from XHS-Downloader config")
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Failed to load cookies from XHS config: {e}")
            return None
    
    def load_from_zhihu_config(self) -> Optional[Dict[str, str]]:
        """
        从知乎配置文件中加载Cookie
        
        Returns:
            Cookie字典，失败返回None
        """
        try:
            # 知乎配置文件路径
            config_path = Path(__file__).parent.parent / "config" / "zhihu_cookie.json"
            
            if not config_path.exists():
                logger.debug(f"Zhihu config not found: {config_path}")
                return None
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 检查是否使用浏览器模式
            if config.get('use_browser', False):
                logger.debug("Zhihu config set to use browser mode")
                return None
            
            cookie_str = config.get('cookie', '')
            if not cookie_str:
                logger.debug("No cookie found in Zhihu config")
                return None
            
            # 将Cookie字符串转换为字典
            cookies_dict = {}
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    key, value = item.split('=', 1)
                    cookies_dict[key.strip()] = value.strip()
            
            logger.info(f"Loaded {len(cookies_dict)} cookies from Zhihu config")
            return cookies_dict
            
        except Exception as e:
            logger.error(f"Failed to load cookies from Zhihu config: {e}")
            return None
    
    def save_to_xhs_config(self, cookie: str) -> bool:
        """
        保存Cookie到小红书下载器配置（统一管理）
        
        Args:
            cookie: Cookie字符串
        
        Returns:
            是否成功
        """
        try:
            # XHS-Downloader 配置文件路径
            config_path = Path(__file__).parent.parent.parent / "XHS-Downloader" / "Volume" / "settings.json"
            
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取或创建配置
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # 更新Cookie
            config['cookie'] = cookie
            
            # 确保有User-Agent
            if not config.get('user_agent'):
                config['user_agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            
            # 保存
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            logger.info(f"Saved cookie to XHS-Downloader config: {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookie to XHS config: {e}")
            return False


# 便捷函数
def get_cookies_for_domain(domain: str, browser: str = 'chrome') -> Optional[Dict[str, str]]:
    """
    获取指定域名的Cookies
    
    Args:
        domain: 目标域名
        browser: 浏览器类型
    
    Returns:
        Cookie字典
    """
    manager = CookieManager()
    return manager.load_from_browser(domain, browser)


def get_xiaohongshu_cookies() -> Optional[Dict[str, str]]:
    """
    获取小红书Cookies（优先使用XHS-Downloader配置）
    
    Returns:
        Cookie字典
    """
    manager = CookieManager()
    
    # 1. 尝试从XHS-Downloader配置加载（优先）
    cookies = manager.load_from_xhs_config()
    if cookies:
        logger.info("Using cookies from XHS-Downloader config")
        return cookies
    
    # 2. 尝试从浏览器加载
    if BROWSER_COOKIE3_AVAILABLE:
        cookies = manager.load_from_browser("xiaohongshu.com", "chrome")
        if cookies:
            logger.info("Using cookies from browser")
            return cookies
    
    logger.warning("No xiaohongshu cookies available")
    return None


def get_zhihu_cookies() -> Optional[Dict[str, str]]:
    """
    获取知乎Cookies（优先使用配置文件，其次浏览器）
    
    Returns:
        Cookie字典
    """
    manager = CookieManager()
    
    # 1. 尝试从配置文件加载（优先）
    cookies = manager.load_from_zhihu_config()
    if cookies:
        logger.info("Using cookies from Zhihu config")
        return cookies
    
    # 2. 尝试从浏览器加载
    if BROWSER_COOKIE3_AVAILABLE:
        try:
            cookies = manager.load_from_browser("zhihu.com", "chrome")
            if cookies:
                logger.info("Using cookies from browser")
                return cookies
        except Exception as e:
            logger.debug(f"Failed to load from browser: {e}")
    
    logger.warning("No zhihu cookies available")
    return None
