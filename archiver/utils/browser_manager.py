"""
DrissionPage 浏览器单例管理器
确保整个应用程序生命周期中只有一个浏览器实例
"""

import atexit
import logging
from typing import Optional
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, Chromium
    DRISSIONPAGE_AVAILABLE = True
except ImportError:
    DRISSIONPAGE_AVAILABLE = False
    logging.warning("DrissionPage not installed. Run: pip install DrissionPage")


logger = logging.getLogger(__name__)


class BrowserManager:
    """
    DrissionPage 浏览器单例管理器
    
    特性：
    - 全局单例：整个应用程序只创建一个浏览器实例
    - 标签页管理：每个任务使用独立的标签页
    - 自动清理：程序退出时自动关闭浏览器
    - 线程安全：支持多任务并发（每个任务一个 tab）
    """
    
    _instance: Optional['BrowserManager'] = None
    _browser: Optional['Chromium'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化（只执行一次）"""
        if not self._initialized:
            self._initialized = True
            # 注册退出时自动清理
            atexit.register(self.cleanup)
            logger.info("浏览器管理器已初始化")
    
    def get_browser(
        self,
        browser_data_dir: str = "./browser_data",
        headless: bool = True,
        **kwargs
    ) -> 'Chromium':
        """
        获取全局浏览器实例（如果不存在则创建）
        
        Args:
            browser_data_dir: 浏览器数据目录（存储 Cookies 和登录态）
            headless: 是否使用无头模式
            **kwargs: 其他浏览器配置参数
        
        Returns:
            Chromium 浏览器实例
        """
        if not DRISSIONPAGE_AVAILABLE:
            raise ImportError("Please install DrissionPage: pip install DrissionPage")
        
        # 如果浏览器已存在且未关闭，直接返回
        if self._browser is not None:
            try:
                # 检查浏览器是否还活着（通过访问属性）
                _ = self._browser.address
                logger.debug("复用现有浏览器实例")
                return self._browser
            except Exception as e:
                logger.warning(f"现有浏览器实例已失效: {e}")
                self._browser = None
        
        # 创建新的浏览器实例
        logger.info("创建全局浏览器实例...")
        
        # Configure browser options
        options = ChromiumOptions()
        
        # 设置端口（避免与其他浏览器实例冲突）
        options.set_local_port(9333)  # 使用不同于默认的 9222 端口
        
        # 使用项目内的独立 Chromium（已配置 LSUIElement 隐藏 Dock 图标）
        # 这样可以：
        # 1. 避免与用户个人 Chrome 冲突
        # 2. 避免 UI 弹窗
        # 3. 通过 Info.plist 配置完全隐藏 Dock 图标 (LSUIElement=1)
        project_chromium = Path(__file__).parent.parent.parent / "chromium/chrome-mac/Chromium.app"
        chromium_executable = project_chromium / "Contents/MacOS/Chromium"
        
        browser_found = False
        if chromium_executable.exists():
            logger.info(f"使用项目独立 Chromium: {chromium_executable}")
            options.set_browser_path(str(chromium_executable))
            browser_found = True
        
        if not browser_found:
            logger.warning(f"未找到项目 Chromium ({chromium_executable})，尝试其他选项...")
            # 优先选项1: Playwright 的 Chromium
            playwright_path = Path.home() / "Library/Caches/ms-playwright"
            if playwright_path.exists():
                chromium_dirs = sorted(list(playwright_path.glob("chromium-*")), reverse=True)
                for d in chromium_dirs:
                    for arch in ["arm64", "x64"]:
                        app_path = d / f"chrome-mac{'-' + arch if arch != 'x64' else ''}/Google Chrome for Testing.app"
                        exe_path = app_path / "Contents/MacOS/Google Chrome for Testing"
                        if exe_path.exists():
                            options.set_browser_path(str(exe_path))
                            logger.info(f"使用 Playwright Chromium: {exe_path}")
                            browser_found = True
                            break
                    if browser_found:
                        break
            
            # 选项2: 系统 Chrome（最后的选择）
            if not browser_found:
                logger.info("使用系统默认浏览器（Chrome）")

        # 设置用户数据目录（保存 Cookies 和登录态）
        # 使用独立目录，完全隔离
        browser_data_path = Path(browser_data_dir)
        browser_data_path.mkdir(exist_ok=True, parents=True)
        options.set_user_data_path(str(browser_data_path.absolute()))
        
        # 无头模式配置
        # DrissionPage 在 macOS 上需要明确设置headless参数，但不使用headless模式
        # 使用 LSUIElement 隐藏 Dock 图标
        # 不过，如果完全不能启动，可能需要使用 new headless 模式
        if headless:
            # 尝试使用新的 headless 模式（Chrome 109+）
            options.set_argument('--headless=new')
        
        # 反爬虫和性能优化配置
        options.set_argument('--no-sandbox')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--disable-blink-features=AutomationControlled')
        options.set_argument('--disable-extensions')
        options.set_argument('--disable-popup-blocking')
        options.set_argument('--disable-notifications')
        options.set_argument('--disable-infobars')
        options.set_argument('--no-first-run')
        options.set_argument('--no-default-browser-check')
        # 移除以下参数，它们可能导致渲染器连接问题：
        # --disable-gpu (可能导致渲染问题)
        # --disable-background-timer-throttling (可能影响页面加载)
        # --disable-backgrounding-occluded-windows
        # --disable-renderer-backgrounding
        
        # 其他自定义配置
        for key, value in kwargs.items():
            if hasattr(options, key):
                getattr(options, key)(value)
        
        # 创建浏览器
        self._browser = Chromium(addr_or_opts=options)
        
        logger.info(f"✓ 浏览器启动成功 (PID: {self._browser.process_id if hasattr(self._browser, 'process_id') else 'N/A'})")
        logger.info(f"  - 用户数据: {browser_data_dir}")
        logger.info(f"  - 无头模式: {headless}")
        
        return self._browser
    
    def new_tab(self, url: str = None, retries: int = 3):
        """
        创建新标签页
        
        Args:
            url: 可选，要访问的 URL
            retries: 重试次数（默认 3 次）
        
        Returns:
            新创建的标签页对象
        """
        if self._browser is None:
            raise RuntimeError("浏览器未初始化，请先调用 get_browser()")
        
        logger.debug(f"创建新标签页: {url or 'about:blank'}")
        
        # 创建新标签页，带重试机制
        for attempt in range(retries):
            try:
                tab = self._browser.new_tab(url=url)
                # 等待标签页稳定
                import time
                time.sleep(1)
                # 验证标签页是否可用
                _ = tab.title  # 触发一次连接检查
                return tab
            except Exception as e:
                logger.warning(f"创建标签页失败 (尝试 {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    import time
                    time.sleep(2)
                else:
                    raise RuntimeError(f"创建标签页失败，已重试 {retries} 次: {e}")
        
        raise RuntimeError("创建标签页失败")
    
    def close_tab(self, tab):
        """
        关闭指定标签页
        
        Args:
            tab: 要关闭的标签页对象
        """
        try:
            if tab:
                tab.close()
                logger.debug("标签页已关闭")
        except Exception as e:
            logger.warning(f"关闭标签页时出错: {e}")
    
    def cleanup(self):
        """
        清理资源：关闭浏览器进程
        
        注意：
        - 此方法会在程序退出时自动调用（通过 atexit）
        - 也可以手动调用来提前清理
        """
        if self._browser is not None:
            try:
                logger.info("正在关闭浏览器...")
                self._browser.quit()
                self._browser = None
                logger.info("✓ 浏览器已彻底关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
    
    def is_alive(self) -> bool:
        """
        检查浏览器是否仍在运行
        
        Returns:
            True 表示浏览器正在运行
        """
        if self._browser is None:
            return False
        
        try:
            _ = self._browser.address
            return True
        except Exception:
            return False
    
    @property
    def browser(self) -> Optional['Chromium']:
        """获取浏览器实例（只读）"""
        return self._browser


# 全局单例实例
_global_browser_manager = BrowserManager()


def get_browser_manager() -> BrowserManager:
    """
    获取全局浏览器管理器单例
    
    Returns:
        BrowserManager 实例
    """
    return _global_browser_manager


# 便捷函数
def get_browser(**kwargs) -> 'Chromium':
    """
    便捷函数：获取全局浏览器实例
    
    Args:
        **kwargs: 浏览器配置参数
    
    Returns:
        Chromium 浏览器实例
    """
    return _global_browser_manager.get_browser(**kwargs)


def new_tab(url: str = None):
    """
    便捷函数：创建新标签页
    
    Args:
        url: 要访问的 URL
    
    Returns:
        新创建的标签页对象
    """
    return _global_browser_manager.new_tab(url=url)


def close_tab(tab):
    """
    便捷函数：关闭标签页
    
    Args:
        tab: 要关闭的标签页对象
    """
    _global_browser_manager.close_tab(tab)


def cleanup_browser():
    """
    便捷函数：清理浏览器资源
    """
    _global_browser_manager.cleanup()
