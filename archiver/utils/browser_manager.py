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


import socket
import tempfile

def find_free_port():
    """找到一个空闲端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

logger = logging.getLogger(__name__)


#region 辅助工具

def _copy_cookies_to_temp(src_profile: Path, dst_profile: Path) -> None:
    """
    将持久化 Chrome 配置目录中的 Cookies 文件拷贝到临时目录，
    使无头实例能复用已登录的会话，同时不与正在运行的浏览器争抢文件锁。
    """
    import shutil

    # Chrome/Chromium 的 Cookies 通常位于 Default/ 子目录，同时需要 Local State 以解密 Cookies (特别是在 macOS 上)
    cookie_files = [
        "Default/Cookies", 
        "Default/Cookies-journal", 
        "Default/Login Data",
        "Default/Network/Cookies",          # 新版 Chrome 路径
        "Default/Network/Cookies-journal",
        "Local State"                       # 用于解密 Cookie
    ]
    copied = []
    for rel in cookie_files:
        src = src_profile / rel
        dst = dst_profile / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(str(src), str(dst))
                copied.append(rel)
            except Exception as e:
                logger.debug(f"拷贝 {rel} 失败（非致命）: {e}")
    if copied:
        logger.info(f"无头模式：已从持久化目录拷贝登录 Cookies ({', '.join(copied)})")
    else:
        logger.info("无头模式：持久化目录暂无 Cookies，将以匿名模式运行")

#endregion


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
    _temp_dirs: list[Path] = []
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._temp_dirs = []
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
        browser_data_dir: Optional[str] = None,
        headless: bool = True,
        **kwargs
    ) -> 'Chromium':
        """
        获取全局浏览器实例（如果不存在则创建）
        
        Args:
            browser_data_dir: 浏览器数据目录（存储 Cookies 和登录态）。如果为 None，默认使用 ./browser_data
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
        
        # 显式分配端口，避免冲突
        try:
            port = find_free_port()
            options.set_local_port(port)
            logger.info(f"分配浏览器端口: {port}")
        except Exception:
            pass # 让 DrissionPage 自动处理
        
        # 使用项目内的独立 Chromium
        project_chromium = Path(__file__).parent.parent.parent / "chromium/chrome-mac/Chromium.app"
        chromium_executable = project_chromium / "Contents/MacOS/Chromium"
        
        if chromium_executable.exists():
            logger.info(f"使用项目独立 Chromium: {chromium_executable}")
            options.set_browser_path(str(chromium_executable))
       
        # 设置用户数据目录
        # 持久化目录用于保存登录态；无头模式下拷贝 Cookies 到临时目录避免文件锁冲突
        if browser_data_dir is None:
            browser_data_dir = "./browser_data"
        persistent_data_path = Path(browser_data_dir)
        persistent_data_path.mkdir(exist_ok=True, parents=True)

        if headless:
            # 在项目目录下新建 temp_file 文件夹以供存放临时 cookie 避免权限问题
            project_root = Path(__file__).parent.parent.parent
            temp_dir_base = project_root / "temp_file"
            temp_dir_base.mkdir(exist_ok=True, parents=True)
            browser_data_path = Path(tempfile.mkdtemp(prefix="memidx_headless_", dir=str(temp_dir_base)))
            self._temp_dirs.append(browser_data_path)
            logger.info(f"无头模式：使用临时用户目录 {browser_data_path}")
            # 将持久化目录中的 Cookies 拷贝到临时目录，保留登录态
            _copy_cookies_to_temp(persistent_data_path, browser_data_path)
        else:
            browser_data_path = persistent_data_path
        options.set_user_data_path(str(browser_data_path.absolute()))

        # 无头模式配置（使用新版 headless 参数，避免旧版兼容性警告）
        if headless:
            options.set_argument('--headless=new')
        
        # 反爬虫 + 防界面干扰配置（参考 7fdc58e 稳定版）
        options.set_argument('--no-sandbox')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--disable-blink-features=AutomationControlled')
        options.set_argument('--disable-extensions')
        options.set_argument('--disable-popup-blocking')
        options.set_argument('--disable-notifications')
        options.set_argument('--disable-infobars')
        options.set_argument('--no-first-run')
        options.set_argument('--no-default-browser-check')
        # 允许所有来源连接调试端口 (解决 Handshake 404 问题)
        options.set_argument('--remote-allow-origins=*')
        options.set_user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        
         # 其他自定义配置
        for key, value in kwargs.items():
            if hasattr(options, key):
                getattr(options, key)(value)
        
        # 创建浏览器 (带重试机制，应对用户数据目录锁定问题)
        try:
            self._browser = Chromium(addr_or_opts=options)
        except Exception as e:
            logger.warning(f"浏览器首次启动失败: {e}")
            logger.warning("尝试使用临时用户数据目录重试...")
            
            # 重试时同样拷贝 Cookie，保留登录态
            project_root = Path(__file__).parent.parent.parent
            temp_dir_base = project_root / "temp_file"
            temp_dir_base.mkdir(exist_ok=True, parents=True)
            _retry_tmp = Path(tempfile.mkdtemp(prefix="memory_index_browser_", dir=str(temp_dir_base)))
            self._temp_dirs.append(_retry_tmp)
            _copy_cookies_to_temp(persistent_data_path, _retry_tmp)
            options.set_user_data_path(str(_retry_tmp))
            
            # 使用新端口
            try:
                new_port = find_free_port()
                options.set_local_port(new_port)
            except:
                pass

            try:
                self._browser = Chromium(addr_or_opts=options)
                logger.info(f"使用临时用户数据目录启动成功: {temp_user_data}")
            except Exception as e2:
                logger.error(f"浏览器启动彻底失败: {e2}")
                raise e2
        
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
        清理资源：关闭浏览器进程并清理临时目录
        
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
        
        # 清理临时目录
        if hasattr(self, '_temp_dirs') and self._temp_dirs:
            import shutil
            for tmp_dir in self._temp_dirs:
                try:
                    if tmp_dir.exists():
                        shutil.rmtree(tmp_dir, ignore_errors=True)
                        logger.info(f"已清理临时目录: {tmp_dir}")
                except Exception as e:
                    logger.debug(f"清理临时目录 {tmp_dir} 失败: {e}")
            self._temp_dirs.clear()
    
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
