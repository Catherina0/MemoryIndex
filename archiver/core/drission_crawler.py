"""
基于 DrissionPage 的网页归档器
使用真实浏览器环境，支持复杂的 JS 渲染和登录态
"""

import os
import time
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("Google GenAI SDK not installed. Run: pip install google-genai")


try:
    from DrissionPage import Chromium
    DRISSIONPAGE_AVAILABLE = True
except ImportError:
    DRISSIONPAGE_AVAILABLE = False
    logging.warning("DrissionPage not installed. Run: pip install DrissionPage")

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False
    logging.warning("html2text not installed. Run: pip install html2text")

from archiver.platforms.base import PlatformAdapter
from archiver.utils.url_parser import detect_platform
from archiver.utils.image_downloader import ImageDownloader
from archiver.utils.browser_manager import get_browser_manager


logger = logging.getLogger(__name__)


class DrissionArchiver:
    """基于 DrissionPage 的网页归档器"""
    
    def __init__(
        self,
        output_dir: str = "archived",
        browser_data_dir: str = "./browser_data",
        headless: bool = True,
        verbose: bool = False
    ):
        """
        初始化归档器
        
        Args:
            output_dir: 输出目录
            browser_data_dir: 浏览器数据目录（存储 Cookies 和登录态）
            headless: 是否使用无头模式
            verbose: 是否输出详细日志
        """
        if not DRISSIONPAGE_AVAILABLE:
            raise ImportError("Please install DrissionPage: pip install DrissionPage")
        
        if not HTML2TEXT_AVAILABLE:
            raise ImportError("Please install html2text: pip install html2text")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.browser_data_dir = Path(browser_data_dir)
        self.browser_data_dir.mkdir(exist_ok=True)
        
        self.headless = headless
        self.verbose = verbose
        
        # 获取浏览器管理器（全局单例）
        self.browser_manager = get_browser_manager()
        
        # 配置 HTML2Text
        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = False
        self.converter.ignore_images = False
        self.converter.body_width = 0
        
        # 当前任务的标签页（每个任务一个 tab）
        self.current_tab = None
        
        # 配置日志
        if verbose:
            logging.basicConfig(level=logging.INFO)
    
    def _init_tab(self):
        """为当前任务创建新标签页（带重试机制）"""
        # 获取全局浏览器实例
        browser = self.browser_manager.get_browser(
            browser_data_dir=str(self.browser_data_dir),
            headless=self.headless
        )
        
        # 创建新标签页（带重试机制）
        tab = self.browser_manager.new_tab()
        logger.info("✓ 新标签页已创建")
        return tab
    
    def _close_tab(self):
        """关闭当前任务的标签页"""
        if self.current_tab is not None:
            try:
                self.browser_manager.close_tab(self.current_tab)
                self.current_tab = None
            except Exception as e:
                logger.debug(f"关闭标签页时出错（可忽略）: {e}")
                self.current_tab = None
    
    def _deduplicate_twitter_images(self, image_urls: list) -> list:
        """
        Twitter 图片去重：移除同一图片的不同尺寸版本
        
        Twitter 图片 URL 格式：
        https://pbs.twimg.com/media/xxxxx?format=jpg&name=small
        https://pbs.twimg.com/media/xxxxx?format=jpg&name=medium
        https://pbs.twimg.com/media/xxxxx?format=jpg&name=large
        https://pbs.twimg.com/media/xxxxx?format=jpg&name=orig
        
        策略：只保留每张图片的最大尺寸版本（优先级：orig > large > medium > small）
        """
        if not image_urls:
            return image_urls
        
        # 按图片ID分组
        image_groups = {}
        size_priority = {'orig': 4, 'large': 3, '4096x4096': 3, 'medium': 2, 'small': 1, '900x900': 1, '360x360': 0}
        
        for url in image_urls:
            if 'twimg.com/media/' in url:
                # 提取图片ID（去除参数）
                base_url = url.split('?')[0]
                
                # 提取尺寸参数
                size = 'medium'  # 默认
                if 'name=' in url:
                    import re
                    match = re.search(r'name=(\w+)', url)
                    if match:
                        size = match.group(1)
                
                # 记录或更新最大尺寸版本
                if base_url not in image_groups:
                    image_groups[base_url] = {'url': url, 'size': size, 'priority': size_priority.get(size, 0)}
                else:
                    current_priority = size_priority.get(size, 0)
                    if current_priority > image_groups[base_url]['priority']:
                        image_groups[base_url] = {'url': url, 'size': size, 'priority': current_priority}
            else:
                # 非 Twitter 图片，直接保留
                image_groups[url] = {'url': url, 'size': 'unknown', 'priority': 999}
        
        # 返回去重后的 URL 列表
        result = [item['url'] for item in image_groups.values()]
        
        if len(result) < len(image_urls):
            logger.info(f"Twitter 图片去重: {len(image_urls)} -> {len(result)} 张（移除了重复尺寸）")
        
        return result
    
    def _load_manual_cookies(self, platform_name: str, url: str):
        """
        加载手动配置的 Cookie（如果存在）
        
        Args:
            platform_name: 平台名称（zhihu, xiaohongshu, bilibili）
            url: 目标URL
        """
        # 配置文件路径
        config_dir = Path(__file__).parent.parent / "config"
        cookie_file = config_dir / f"{platform_name}_drission_cookie.txt"
        
        if not cookie_file.exists():
            logger.debug(f"未找到手动配置的 Cookie: {cookie_file}")
            return False
        
        try:
            # 读取 Cookie
            with open(cookie_file, 'r', encoding='utf-8') as f:
                cookie_string = f.read().strip()
            
            if not cookie_string:
                logger.warning(f"Cookie 文件为空: {cookie_file}")
                return False
            
            logger.info(f"加载手动配置的 Cookie: {platform_name}")
            
            # 确保已访问对应平台的页面（Cookie 需要域名）
            if not self.current_tab.url or self.current_tab.url == 'about:blank':
                logger.info(f"首次访问页面以设置 Cookie...")
                try:
                    # 根据平台访问主页以设置 cookie
                    target_url = url
                    if platform_name == 'xiaohongshu':
                        target_url = "https://www.xiaohongshu.com/explore"
                    elif platform_name == 'bilibili':
                        target_url = "https://www.bilibili.com"
                    elif platform_name == 'zhihu':
                        target_url = "https://www.zhihu.com"
                        
                    self.current_tab.set.timeouts(page_load=15)
                    self.current_tab.get(target_url)
                except Exception as e:
                    logger.warning(f"首次访问可能未完全加载: {e}")
                time.sleep(1)
            
            # 解析并设置 Cookie
            # 格式：name1=value1; name2=value2; ...
            cookie_pairs = [pair.strip() for pair in cookie_string.split(';') if pair.strip()]
            
            for pair in cookie_pairs:
                if '=' not in pair:
                    continue
                
                name, value = pair.split('=', 1)
                name = name.strip()
                value = value.strip()
                
                # 获取平台特定域名
                cookie_domain = self._get_cookie_domain(url)
                if platform_name == 'xiaohongshu':
                    cookie_domain = ".xiaohongshu.com"
                elif platform_name == 'bilibili':
                    cookie_domain = ".bilibili.com"
                elif platform_name == 'zhihu':
                    cookie_domain = ".zhihu.com"
                
                try:
                    # 设置 Cookie
                    self.current_tab.set.cookies({
                        'name': name,
                        'value': value,
                        'domain': cookie_domain,
                        'path': '/'
                    })
                    logger.debug(f"✓ 设置 Cookie: {name}")
                except Exception as e:
                    logger.warning(f"✗ 设置 Cookie 失败 {name}: {e}")
            
            logger.info(f"✓ 成功加载 {len(cookie_pairs)} 个 Cookie")
            
            # 刷新页面使 Cookie 生效
            logger.info("刷新页面...")
            self.current_tab.refresh()
            time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"加载手动 Cookie 失败: {e}")
            return False
    
    def _get_cookie_domain(self, url: str) -> str:
        """从 URL 提取 Cookie 域名"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        # 返回 .domain.com 格式
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) >= 2:
            return f".{'.'.join(domain_parts[-2:])}"
        return parsed.netloc

    def capture_screenshot(self, url: str, output_path: Path):
        """
        仅截取网页截图 (复用归档器的浏览器环境和反爬策略)
        """
        from archiver.utils.url_parser import detect_platform, extract_url_from_text
        
        # 确保 URL 有效
        clean_url = extract_url_from_text(url)
        if not clean_url:
            clean_url = url
            
        logger.info(f"📸 开始截图任务: {clean_url}")
        
        # 初始化标签页
        if self.current_tab:
            self._close_tab()
        self.current_tab = self._init_tab()
        
        try:
            # 1. 检测平台并加载 Cookie
            platform_name = detect_platform(clean_url)
            logger.info(f"检测平台: {platform_name}")
            
            if platform_name in ['zhihu', 'xiaohongshu', 'bilibili', 'twitter']:
                self._load_manual_cookies(platform_name, clean_url)
                
            # 2. 访问页面
            logger.info(f"正在访问 (为截图): {clean_url}")
            self.current_tab.get(clean_url)
            self.current_tab.wait.load_start()
            
            # 等待足够的时间确保内容渲染
            wait_time = 5 if platform_name in ['twitter', 'bilibili', 'xiaohongshu'] else 3
            time.sleep(wait_time)
            
            # 3. 滚动加载懒加载内容
            logger.info("滚动页面以触发懒加载...")
            try:
                self.current_tab.scroll.to_bottom()
                time.sleep(2)
                self.current_tab.scroll.to_top()
            except Exception as _e:
                logger.debug(f"标准滚动失败，尝试备用滚动: {_e}")
                try:
                    self.current_tab.run_js("window.scrollTo(0, document.body.scrollHeight || 10000);")
                    time.sleep(2)
                    self.current_tab.run_js("window.scrollTo(0, 0);")
                except Exception as _e2:
                    logger.debug(f"备用滚动也失败（忽略）: {_e2}")
            time.sleep(1)
            
            # 4. 全页截图
            logger.info(f"正在保存全页截图: {output_path.name}")
            # 确保存储目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.current_tab.get_screenshot(path=str(output_path), full_page=True)
            logger.info("✅ 截图完成")
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise e
        finally:
            self._close_tab()
    
    def archive(
        self,
        url: str,
        platform_adapter: Optional[PlatformAdapter] = None,
        mode: str = "default",
        generate_report: bool = False,
        with_ocr: bool = False,
        screenshot_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL（支持分享文本格式，会自动提取URL）
            platform_adapter: 平台适配器（如果为None则自动检测）
            mode: 归档模式 (default=只提取正文/full=完整内容含评论)
            generate_report: 是否生成 LLM 结构化报告
            with_ocr: 是否对下载的图片进行OCR识别
            screenshot_ocr: 是否仅对全页截图进行OCR识别 (with_ocr=True时会自动包含此项)
        
        Returns:
            包含归档结果的字典
        """
        # 从输入文本中提取 URL（支持分享文本格式）
        from archiver.utils.url_parser import extract_url_from_text
        original_input = url
        url = extract_url_from_text(url)
        
        if not url:
            return {
                'success': False,
                'error': '无法从输入中提取有效的URL',
                'input': original_input
            }
        
        # 如果提取的URL与输入不同，记录日志
        if url != original_input:
            logger.info(f"从分享文本中提取URL: {url}")
        
        logger.info(f"开始归档: {url}")
        
        # 为此任务创建新标签页
        self.current_tab = self._init_tab()
        
        try:
            # 自动检测平台
            if platform_adapter is None:
                platform_name = detect_platform(url)
                logger.info(f"检测平台: {platform_name} (模式: {mode})")
                from archiver.platforms import (
                    ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
                    RedditAdapter, WordPressAdapter, TwitterAdapter
                )
                
                adapters = {
                    "zhihu": ZhihuAdapter(),
                    "xiaohongshu": XiaohongshuAdapter(),
                    "bilibili": BilibiliAdapter(),
                    "reddit": RedditAdapter(),
                    "twitter": TwitterAdapter(),
                    "wordpress": WordPressAdapter(),
                }
                platform_adapter = adapters.get(platform_name, WordPressAdapter())
            
            # 访问页面（带重试机制）
            logger.info(f"正在访问: {url}")
            
            # 尝试加载手动配置的 Cookie
            if platform_adapter.name in ['zhihu', 'xiaohongshu', 'bilibili', 'twitter']:
                self._load_manual_cookies(platform_adapter.name, url)
            
            # 重试访问页面
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.current_tab.get(url)
                    # 智能等待页面加载
                    self.current_tab.wait.load_start()
                    time.sleep(2)  # 等待 JS 执行
                    break
                except Exception as e:
                    logger.warning(f"访问页面失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        # 重新创建标签页
                        self._close_tab()
                        self.current_tab = self._init_tab()
                    else:
                        raise RuntimeError(f"访问页面失败，已重试 {max_retries} 次: {e}")
            
            # 检查是否需要登录（推特特殊处理）
            if platform_adapter.name == 'twitter':
                current_url = self.current_tab.url
                if 'login' in current_url or 'i/flow/login' in current_url:
                    logger.warning("⚠️  推特需要登录才能查看内容")
                    logger.info("💡 请运行以下命令登录推特：")
                    logger.info("   make login-twitter")
                    logger.info("   或者访问 https://twitter.com 手动登录")
                    return {
                        "success": False,
                        "error": "推特需要登录。请运行 'make login-twitter' 登录账号",
                        "url": url
                    }
            
            # 滚动页面确保懒加载内容加载完成
            logger.info("滚动页面加载懒加载内容...")
            try:
                self.current_tab.scroll.to_bottom()
                time.sleep(1)
                self.current_tab.scroll.to_top()
            except Exception as _e:
                logger.debug(f"标准滚动失败，尝试备用滚动: {_e}")
                try:
                    self.current_tab.run_js("window.scrollTo(0, document.body.scrollHeight || 10000);")
                    time.sleep(1)
                    self.current_tab.run_js("window.scrollTo(0, 0);")
                except Exception as _e2:
                    logger.debug(f"备用滚动也失败（忽略）: {_e2}")
            time.sleep(1)
            
            # 获取页面标题
            page_title = self.current_tab.title
            if not page_title:
                page_title = "Untitled"

            # 🔒 检测登录墙 / 安全拦截页
            _current_url = self.current_tab.url or url
            _blocked_titles = ["安全限制", "验证", "登录", "sign in", "login", "access denied", "forbidden"]
            _blocked_url_keywords = ["login", "signin", "passport", "account/login", "captcha", "security"]
            _is_blocked = (
                any(kw in page_title.lower() for kw in _blocked_titles)
                or any(kw in _current_url.lower() for kw in _blocked_url_keywords)
            )
            
            # 如果看起来是被屏蔽，但实际上核心元素还在，那属于误判，允许继续提取
            if _is_blocked and platform_adapter and getattr(platform_adapter, 'content_selector', ''):
                _test_selector = platform_adapter.content_selector.split(',')[0].strip()
                try:
                    if self.current_tab.ele(_test_selector, timeout=1):
                        logger.info("📍 检测到登录关键字，但页面仍包含核心内容，跳过拦截")
                        _is_blocked = False
                except Exception:
                    pass

            if _is_blocked:
                # 直接映射到 Makefile 中已有的 cookie 配置目标
                _PLATFORM_COOKIE_CMD = {
                    "xiaohongshu": "make config-xhs-cookie",
                    "xhs":         "make config-xhs-cookie",
                    "zhihu":       "make config-zhihu-cookie",
                }
                _platform_hint = platform_adapter.name if platform_adapter else "xiaohongshu"
                _cookie_cmd = _PLATFORM_COOKIE_CMD.get(_platform_hint, "make config-xhs-cookie")
                logger.error(
                    f"🔒 页面被拦截（标题: 「{page_title}」，当前URL: {_current_url}）\n"
                    f"   原因: 未登录或 Cookie 已过期\n"
                    f"   ━━━━ 解决方法 ━━━━\n"
                    f"   1️⃣  浏览器登录（推荐，一次搞定所有平台）：\n"
                    f"         make login\n"
                    f"   2️⃣  平台专用 Cookie 配置：\n"
                    f"         {_cookie_cmd}\n"
                    f"   3️⃣  调试模式（可见浏览器，手动操作）：\n"
                    f"         make archive-visible URL=\"{url}\"\n"
                    f"   ━━━━━━━━━━━━━━━━━━"
                )
                return {
                    "success": False,
                    "error": (
                        f"页面被拦截（{page_title}）：Cookie 未配置或已过期。\n"
                        f"请运行 `make login` 在浏览器中登录（一次搞定所有平台），\n"
                        f"或运行 `{_cookie_cmd}` 使用平台专用配置，\n"
                        f"或运行 `make archive-visible URL=\"{url}\"` 调试模式重试。"
                    ),
                    "url": url,
                    "blocked": True,
                    "fix_commands": [
                        "make login",
                        _cookie_cmd,
                        f'make archive-visible URL="{url}"',
                    ],
                }

            # 🆕 提前截图：在内容提取之前拍摄，避免反爬重定向导致截图为白页
            # 此时页面已加载并滚动到顶部，是截图的最佳时机
            _pre_screenshot_path = self.output_dir / f"_tmp_screenshot_{datetime.now().strftime('%H%M%S%f')}.png"
            try:
                logger.info("📸 正在截取全页截图（内容提取前）...")
                
                if platform_adapter.name == 'twitter':
                    logger.info("  - 优化推特截图：设置视口为 2999x11212触发组件渲染...")
                    # （因为有DPR缩放比，所以/2） 
                    try:
                        self.current_tab.set.window.size(1500, 6666)
                    except Exception as e:
                        logger.debug(f"调整窗口大小遇到错误 (忽略): {e}")
                    
                    time.sleep(1)
                    # 滑动一段距离（让图片区域进入可视渲染线）
                    self.current_tab.scroll.down(2000)
                    time.sleep(1.5)
                    # 进行一次截图（强制底层绘制过程完成）
                    self.current_tab.get_screenshot(path=str(_pre_screenshot_path))
                    # 然后再滑动一次，并最终截图
                    self.current_tab.scroll.to_top()
                    time.sleep(1)
                    self.current_tab.get_screenshot(path=str(_pre_screenshot_path))
                else:
                    self.current_tab.get_screenshot(
                        path=str(_pre_screenshot_path),
                        full_page=True
                    )
                    
                logger.info(f"✅ 截图已完成")
            except Exception as _e:
                logger.warning(f"⚠️  预截图失败（将跳过截图）: {_e}")
                _pre_screenshot_path = None

            # 🆕 提前提取图片URL（从完整页面）
            full_page_html = self.current_tab.html
            logger.info("从完整页面提取图片URL...")
            
            # 提取内容
            content_html = self._extract_content(platform_adapter, mode=mode)
            
            if not content_html:
                return {
                    "success": False,
                    "error": "无法提取页面内容",
                    "url": url
                }
            
            # 转换为 Markdown
            markdown_content = self._convert_to_markdown(
                html=content_html,
                title=page_title,
                url=url,
                platform=platform_adapter.name,
                mode=mode
            )
            
            # 提取纯内容（去掉 YAML frontmatter）
            content_lines = markdown_content.split('\n')
            content_start = 0
            
            # 跳过 YAML frontmatter
            if content_lines and content_lines[0].strip() == '---':
                for i, line in enumerate(content_lines[1:], 1):
                    if line.strip() == '---':
                        content_start = i + 1
                        break
            
            # 纯OCR内容（不含元信息）
            pure_ocr_content = '\n'.join(content_lines[content_start:]).strip()
            
            # 创建文件夹
            folder_name = self._generate_folder_name(page_title, platform_adapter.name)
            folder_path = self.output_dir / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)

            # 全页长截图：将预先截好的临时文件移动到最终位置
            screenshot_path = folder_path / "screenshot.png"
            if _pre_screenshot_path and Path(_pre_screenshot_path).exists():
                import shutil
                shutil.move(str(_pre_screenshot_path), str(screenshot_path))
                logger.info(f"✅ 截图已保存: {screenshot_path.name}")
            else:
                # 临时截图不存在，尝试再次截图（降级方案）
                try:
                    logger.info("📸 降级：重新尝试截图...")
                    self.current_tab.get_screenshot(
                        path=str(screenshot_path),
                        full_page=True
                    )
                    logger.info(f"✅ 截图已保存: {screenshot_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️  截图失败（可忽略）: {e}")

            # 下载图片
            logger.info("开始下载图片...")
            image_downloader = ImageDownloader(
                output_dir=str(folder_path / "images"),
                format="jpg"
            )
            
            # 提取图片URL
            # 默认只从内容提取，特殊情况（如无法提取到内容图片）才从全页提取
            image_urls = image_downloader.extract_image_urls(content_html, url)
            
            # 推特特殊处理：完整模式下，或者内容提取不到图片时，尝试从完整页面提取
            if platform_adapter.name == 'twitter':
                if mode == 'full' or not image_urls:
                    logger.info("推特：尝试从完整页面提取图片...")
                    more_urls = image_downloader.extract_image_urls(full_page_html, url)
                    image_urls = list(set(image_urls + more_urls))
                
                # 调试：显示原始提取的图片 URL
                logger.debug(f"原始提取的图片 URLs: {image_urls}")
            
            # 过滤图片（针对默认模式）
            if image_urls and mode == 'default':
                # 推特：移除头像和表情包，只保留媒体图片
                if platform_adapter.name == 'twitter':
                    filtered_urls = []
                    for img_url in image_urls:
                        # 排除头像 (profile_images)
                        if 'profile_images' in img_url:
                            continue
                        # 排除小图标/表情 (emoji)
                        if 'emoji' in img_url:
                            continue
                        filtered_urls.append(img_url)
                    
                    if len(filtered_urls) < len(image_urls):
                        logger.info(f"过滤了 {len(image_urls) - len(filtered_urls)} 张无关图片（头像/表情）")
                    image_urls = filtered_urls
                
                # Twitter 图片去重（移除同一图片的不同尺寸版本）
                if platform_adapter.name == 'twitter':
                    image_urls = self._deduplicate_twitter_images(image_urls)
            
            # 🔒 稀疏内容检测与增强
            # 如果正文内容过少且图片也少，可能是反爬或动态加载失败
            # 此时强制启用 OCR 和 LLM 报告生成，利用全页截图挽救数据
            min_text_len = 200
            min_image_count = 3
            
            # Twitter/X 和 微博 等短内容平台特殊阈值
            if platform_adapter.name in ['twitter', 'weibo']:
                 min_text_len = 50
                 min_image_count = 1
                 
            if len(pure_ocr_content) < min_text_len and len(image_urls) < min_image_count:
                logger.warning(f"⚠️  检测到内容稀疏 (文本: {len(pure_ocr_content)}字符, 图片: {len(image_urls)}张)")
                logger.info("🚀 自动启动 [OCR增强] 与 [LLM报告生成] 模式以挽救数据")
                with_ocr = True
                generate_report = True

            url_mapping = {}
            if image_urls:
                logger.info(f"发现 {len(image_urls)} 张图片")
                
                # 获取当前站点的 Cookies 用于下载需要权限的图片
                page_cookies = {}
                try:
                    raw_cookies = self.current_tab.cookies()
                    if isinstance(raw_cookies, dict):
                        page_cookies = raw_cookies
                    elif isinstance(raw_cookies, list):
                        for c in raw_cookies:
                            if isinstance(c, dict):
                                page_cookies[c.get('name', '')] = c.get('value', '')
                except Exception as e:
                    logger.debug(f"提取 Cookies 失败: {e}")

                # 修复: 小红书图片的 Referer 必须是 https://www.xiaohongshu.com/
                # 如果传入原始分享链接 (http://xhslink.com/...) 会导致 403 Forbidden
                download_referer = url
                if platform_adapter.name == 'xiaohongshu':
                    download_referer = 'https://www.xiaohongshu.com/'
                
                url_mapping = image_downloader.download_all(
                    image_urls, 
                    referer=download_referer,
                    cookies=page_cookies if page_cookies else None
                )
                
                # 更新markdown中的图片链接
                if url_mapping:
                    for orig_url, local_path in url_mapping.items():
                        rel_path = f"images/{local_path}"
                        markdown_content = markdown_content.replace(orig_url, rel_path)
                    logger.info(f"已更新 {len(url_mapping)} 个图片链接")
            
            # 1. 保存 archive_raw.md（网页内容+图片引用，不含元信息）
            archive_raw_path = folder_path / "archive_raw.md"
            with open(archive_raw_path, "w", encoding="utf-8") as f:
                # 更新图片链接后的纯内容
                updated_pure_content = pure_ocr_content
                if url_mapping:
                    for orig_url, local_path in url_mapping.items():
                        rel_path = f"images/{local_path}"
                        updated_pure_content = updated_pure_content.replace(orig_url, rel_path)
                f.write(updated_pure_content)
            logger.info(f"✅ 保存网页归档原始数据: {archive_raw_path.name}")
            
            # 1.5 如果启用OCR，对图片进行识别
            ocr_text = ""
            if with_ocr and image_urls and url_mapping:
                logger.info(">> 开始OCR识别内容图片...")
                ocr_text = self._perform_ocr_on_images(folder_path / "images")
                
                if ocr_text.strip():
                    ocr_raw_path = folder_path / "ocr_raw.md"
                    with open(ocr_raw_path, "w", encoding="utf-8") as f:
                        ocr_content = f"# 🔍 图片OCR识别结果\n\n"
                        ocr_content += f"**识别时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}  \n"
                        ocr_content += f"**图片数量**: {len(url_mapping)}  \n"
                        ocr_content += f"**识别字符数**: {len(ocr_text)}  \n\n"
                        ocr_content += "---\n\n"
                        ocr_content += ocr_text
                        f.write(ocr_content)
                    logger.info(f"✅ 保存OCR识别结果: {ocr_raw_path.name} ({len(ocr_text)} 字符)")
                else:
                    logger.info("ℹ️  内容图片未识别到文字")
            
            # 1.6 全页截图 OCR (新增)
            # 如果启用了 with_ocr，或者显式启用了 screenshot_ocr，则对截图进行 OCR
            screenshot_ocr_text = ""
            if (with_ocr or screenshot_ocr) and screenshot_path.exists():
                logger.info(">> 开始OCR识别全页截图...")
                screenshot_ocr_text = self._perform_ocr_on_file(screenshot_path)
                
                if screenshot_ocr_text.strip():
                    screenshot_ocr_path = folder_path / "screenshot_OCR.md"
                    with open(screenshot_ocr_path, "w", encoding="utf-8") as f:
                        f.write(f"# 全页截图 OCR 结果\n\n{screenshot_ocr_text}")
                    logger.info(f"✅ 保存截图OCR结果: {screenshot_ocr_path.name} ({len(screenshot_ocr_text)} 字符)")
                else:
                    logger.info("ℹ️  截图未识别到文字")

            # 2. 保存 README.md（元信息 + 引用）
            readme_content = f"""---
title: {page_title}
url: {url}
platform: {platform_adapter.name}
archived_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

# {page_title}

**来源**: [{url}]({url})  
**平台**: {platform_adapter.name}  
**归档时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 📄 原始内容

详见 [archive_raw.md](archive_raw.md)（网页内容+图片）

## 🖼️ 页面截图

详见 [screenshot.png](screenshot.png)（全页长截图）
"""
            if screenshot_ocr_text.strip():
                readme_content += "\n## 📝 截图识别文字\n\n详见 [screenshot_OCR.md](screenshot_OCR.md)（全页 OCR 识别结果）\n"

            readme_content += """
---

> 💡 **提示**: 使用 `report.md` 查看 LLM 处理后的结构化内容
"""
            
            md_filename = "README.md"
            md_path = folder_path / md_filename
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            logger.info(f"归档成功: {folder_path}")
            logger.info(f"  - README: {md_path.name}")
            logger.info(f"  - 归档原始: {archive_raw_path.name}")
            if image_urls:
                logger.info(f"  - 图片: {len(url_mapping)}/{len(image_urls)} 张")
            
            # 3. 生成 report.md（仅在需要时）
            if generate_report:
                logger.info("ℹ️  跳过局部 report.md 生成和 LLM 文件夹重命名（已统一移至 archive_processor 处理）")
            else:
                logger.info("ℹ️  跳过 report.md 生成和 LLM 文件夹重命名（使用 --generate-report 启用）")
            
            return {
                "success": True,
                "url": url,
                "platform": platform_adapter.name,
                "output_path": str(folder_path),
                "markdown_path": str(md_path),
                "title": page_title,
                "content_length": len(markdown_content),
                "images_downloaded": len(url_mapping) if image_urls else 0,
                "images_total": len(image_urls) if image_urls else 0,
                "ocr_enabled": with_ocr,
                "ocr_text_length": len(ocr_text) if with_ocr else 0,
                "screenshot_path": str(screenshot_path) if screenshot_path.exists() else None
            }
            
        except Exception as e:
            logger.error(f"归档失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
        finally:
            # 任务结束，关闭标签页（浏览器保持运行）
            self._close_tab()
            # 注意：浏览器会在程序退出时通过 atexit 自动关闭
    
    def _extract_content(self, platform_adapter: PlatformAdapter, mode: str = "default") -> str:
        """
        提取页面内容
        
        Args:
            platform_adapter: 平台适配器
            mode: 归档模式 ('default' 或 'full')
                  default: 仅保留正文和图片，移除评论、侧边栏等无关元素
                  full: 保留选定容器内的所有内容
        """
        selector = platform_adapter.content_selector
        exclude_selector = platform_adapter.exclude_selector if hasattr(platform_adapter, 'exclude_selector') else ""
        
        # 检测是否需要登录（常见登录提示）
        login_indicators = [
            "登录后推荐",
            "马上登录",
            "请先登录",
            "Sign in",
            "Log in",
            "登入"
        ]
        
        page_text = self.current_tab.html
        for indicator in login_indicators:
            if indicator in page_text:
                # 检查是否有实际内容（登录提示通常文本很短）
                if len(self.current_tab.ele('body', timeout=1).text.strip()) < 500:
                    logger.warning(f"⚠️  检测到登录提示: {indicator}")
                    logger.warning("   建议操作：")
                    logger.warning("   1. 运行 'make login' 登录并保存登录态")
                    logger.warning("   2. 或运行 'make config-drission-cookie' 手动配置Cookie")
                    break
        
        # 尝试使用选择器提取内容
        if platform_adapter.name == 'twitter' and mode == 'default':
            try:
                logger.info("Twitter: 尝试构建纯净内容 (Text + Photos)...")
                
                # 1. 优先尝试查找 Twitter Article (长文章)
                # 尝试多种可能的长文章容器选择器
                article_selectors = [
                    "[data-testid='twitterArticleRichTextView']",  # Draft.js 富文本容器 (优先)
                    "[data-testid='twitterArticleReadView']",      # 阅读视图容器
                    "[data-testid='longformRichTextComponent']"    # 长文组件
                ]
                
                for selector in article_selectors:
                    article_view = self.current_tab.ele(f"css:{selector}")
                    if article_view:
                        logger.info(f"  - 找到 Twitter Article长文容器 {selector}")
                        return article_view.html

                # 2. 收集对话线: 获取 inline_reply_offscreen 上方的所有推文
                nodes = self.current_tab.eles('css:article, [data-testid="inline_reply_offscreen"]')
                
                valid_articles = []
                for node in nodes:
                    if node.attrs.get('data-testid') == 'inline_reply_offscreen':
                        logger.info("  - 遇到回复框 inline_reply_offscreen，停止收集后续推文")
                        break
                    
                    if node.tag == 'article':
                        valid_articles.append(node)
                
                if not valid_articles:
                    logger.warning("  - ❌ 未找到任何推文容器 article")
                    return ""

                logger.info(f"  - 找到 {len(valid_articles)} 个层级推文（对话线）")
                
                thread_html_parts = []
                
                for idx, article in enumerate(valid_articles):
                    parts = []
                    logger.info(f"  - 开始处理推文 {idx + 1}/{len(valid_articles)}...")
                    
                    # 辅助函数：提取文字和图片
                    def extract_tweet_content(container, prefix=""):
                        c_parts = []
                        # 提取正文
                        logger.info(f"{prefix}    - 尝试提取正文...")
                        text_div = container.ele("css:[data-testid='tweetText']", timeout=0.5)
                        if not text_div:
                            text_div = container.ele("xpath:.//*[@data-testid='tweetText']", timeout=0.5)
                        if not text_div:
                            text_div = container.ele("css:div[lang]", timeout=0.5)
                            
                        if text_div:
                            logger.info(f"{prefix}    - 找到正文 (长度: {len(text_div.text)})")
                            c_parts.append(text_div.html)
                        else:
                            logger.warning(f"{prefix}    - ❌ 未找到正文 [data-testid='tweetText']")
                            
                        # 提取图片
                        logger.info(f"{prefix}    - 尝试查找图片...")
                        photos = container.eles("css:[data-testid='tweetPhoto']", timeout=0.5)
                        if not photos:
                            photos = container.eles("xpath:.//*[@data-testid='tweetPhoto']", timeout=0.5)
                            
                        if photos:
                            logger.info(f"{prefix}    - 找到 {len(photos)} 个图片容器")
                            for p in photos:
                                html_part = p.html
                                if 'name=' in html_part:
                                    import re
                                    html_part = re.sub(r'name=(small|medium|360x360|900x900)', 'name=large', html_part)
                                c_parts.append(html_part)
                        else:
                            logger.info(f"{prefix}    - ❌ 未找到图片容器，尝试扫描普通 img 标签...")
                            # 兜底：直接找img
                            imgs = container.eles("css:img", timeout=0.5)
                            valid_imgs = []
                            for img in imgs:
                                src = img.attrs.get('src', '')
                                if 'profile_images' in src or 'emoji' in src:
                                    continue
                                if src:
                                    valid_imgs.append(f'<img src="{src}" />')
                            if valid_imgs:
                                logger.info(f"{prefix}    - 扫描到 {len(valid_imgs)} 张有效图片")
                                c_parts.extend(valid_imgs)
                        
                        return c_parts

                    # 检查是否有长文组件在 tweet 内部
                    has_long_article = False
                    logger.info(f"  - [{idx + 1}] 检查是否为长文章结构...")
                    for comp_selector in article_selectors:
                        long_view = article.ele(f"css:{comp_selector}", timeout=0.5)
                        if long_view:
                            logger.info(f"  - [{idx + 1}] ✅ 在 article 内部找到长文章组件: {comp_selector}")
                            parts.append(long_view.html)
                            has_long_article = True
                            break
                            
                    if not has_long_article:
                        # 提取当前推文的内容
                        main_content = extract_tweet_content(article, f"  - [{idx + 1}]")
                        
                        # 提取引用推文 (Quote Tweet)
                        quote_html = ""
                        logger.info(f"  - [{idx + 1}] 检查是否有嵌套的引用推文 (Quote Tweet)...")
                        quote_container = article.ele('css:div[role="link"]', timeout=0.5)
                        if quote_container:
                            logger.info(f"  - [{idx + 1}] 发现引用推文区域，进行下钻提取...")
                            quote_parts = extract_tweet_content(quote_container, f"  - [引用]")
                            if quote_parts:
                                logger.info(f"  - [{idx + 1}] ✅ 成功提取引用推文内容")
                                quote_html = f"<blockquote>{'<br>'.join(quote_parts)}</blockquote>"
                                
                                # 将主推文的正文与引用的内容分离开，去重防止嵌套重复抓取
                                clean_main = []
                                for part in main_content:
                                    if part not in quote_parts:
                                        clean_main.append(part)
                                main_content = clean_main
                                
                        parts.extend(main_content)
                        if quote_html:
                            parts.append(quote_html)

                    if parts:
                        thread_html_parts.append("\n<br>\n".join(parts))
                        logger.info(f"  - [{idx + 1}] ✅ 当前层级合并完成\n")
                    else:
                        # 兜底
                        logger.warning(f"  - [{idx + 1}] ⚠️ 提取不到明确正文，使用整块内容兜底\n")
                        thread_html_parts.append(article.html)

                if thread_html_parts:
                    # 使用 <hr> 分割多条推文，以便在 Markdown 中显示分割线
                    combined_html = "\n<hr>\n".join(thread_html_parts)
                    return combined_html
                else:
                    logger.warning("  - ❌ 未提取到推文正文")


            except Exception as e:
                logger.warning(f"Twitter 纯净提取失败: {e}, 将尝试通用选择器")
                import traceback
                logger.warning(traceback.format_exc())

        if selector:
            for sel in selector.split(','):
                sel = sel.strip()
                element = self.current_tab.ele(sel, timeout=2)
                if element:
                    # 如果不是全量模式，且定义了排除选择器，尝试移除无关元素
                    # 注意：DrissionPage 的元素操作通常是即时的，这里我们直接操作页面上的元素
                    # 但为了不破坏页面结构影响后续（虽然我们很快就关闭），或者为了处理方便
                    # 我们主要通过 BeautifulSoup 后处理，或者在这里尝试移除
                    
                    if mode == "default" and exclude_selector:
                        logger.info(f"清理模式: 移除无关元素")
                        
                        # 1. 移除配置中定义的元素
                        for exclude in exclude_selector.split(','):
                            exclude = exclude.strip()
                            if not exclude:
                                continue
                            
                            try:
                                unwanted_elements = element.eles(exclude)
                                removed_count = 0
                                for unwanted in unwanted_elements:
                                    self.current_tab.run_js("arguments[0].remove()", unwanted)
                                    removed_count += 1
                                if removed_count > 0:
                                    logger.info(f"  - 已移除 {removed_count} 个 {exclude} 元素")
                            except Exception as e:
                                logger.debug(f"  - 移除 {exclude} 失败: {e}")
                        
                        # 2. 对于小红书，额外移除作者信息和关注按钮
                        if platform_adapter.name == "xiaohongshu":
                            # 移除用户profile链接（作者头像和名字）
                            try:
                                profile_links = element.eles('a[href*="/user/profile"]')
                                if profile_links:
                                    logger.info(f"  - 已移除 {len(profile_links)} 个用户profile链接")
                                    for link in profile_links:
                                        self.current_tab.run_js("arguments[0].remove()", link)
                            except Exception:
                                pass
                            
                            # 移除"关注"按钮 - 通过文字内容匹配
                            try:
                                # 使用更高效的选择器，避免遍历所有div和button
                                follow_btns = element.eles('text:关注')
                                if follow_btns:
                                    logger.info(f"  - 已移除 {len(follow_btns)} 个关注按钮")
                                    for btn in follow_btns:
                                        self.current_tab.run_js("arguments[0].remove()", btn)
                            except Exception as e:
                                logger.debug(f"移除关注按钮失败: {e}")
                    
                    # 重新获取 HTML (移除元素后)
                    html = element.html
                    # 检查是否有实际内容
                    if html and len(html) > 1000:
                        logger.info(f"使用选择器提取内容: {sel}")
                        return html
        
        # 回退：使用通用选择器
        for fallback in ['article', 'main', 'body']:
            element = self.current_tab.ele(fallback, timeout=2)
            if element:
                logger.info(f"使用回退选择器: {fallback}")
                return element.html
        
        # 最后的回退：整个页面
        logger.warning("使用整个页面作为内容")
        return self.current_tab.html
    
    def _convert_to_markdown(
        self,
        html: str,
        title: str,
        url: str,
        platform: str,
        mode: str = "default"
    ) -> str:
        """将 HTML 转换为 Markdown"""
        # 添加元数据头部
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        metadata = f"""---
title: {title}
url: {url}
platform: {platform}
archived_at: {timestamp}
---

"""
        
        # 转换 HTML
        markdown_content = self.converter.handle(html)
        
        # 如果是默认模式，做额外的 Markdown 清洗
        if mode == "default":
            import re
            # 小红书：移除用户profile链接
            if platform == "xiaohongshu":
                # 移除用户profile链接 (格式: [![...](images/...jpg)](/user/profile/...)文字)
                markdown_content = re.sub(
                    r'\[!\[.*?\]\(images/.*?\)\]\(/user/profile/[^\)]+\)\[.*?\]\(/user/profile/[^\)]+\)\s*',
                    '',
                    markdown_content
                )
                # 移除单独的用户链接 (格式: [用户名](/user/profile/...))
                markdown_content = re.sub(
                    r'\[.*?\]\(/user/profile/[^\)]+\)\s*',
                    '',
                    markdown_content
                )
                # 移除单独的"关注"文字
                markdown_content = re.sub(r'^\s*关注\s*$', '', markdown_content, flags=re.MULTILINE)
            
            # 推特：移除用户profile链接和互动按钮
            elif platform == "twitter":
                # 移除用户profile链接 (/@username)
                markdown_content = re.sub(
                    r'\[@[^\]]+\]\(/[^\)]+\)\s*',
                    '',
                    markdown_content
                )
                # 移除互动数字（转推、点赞等）
                markdown_content = re.sub(
                    r'^\s*\d+\s*(Retweets?|Likes?|Replies?|Views?)\s*$',
                    '',
                    markdown_content,
                    flags=re.MULTILINE
                )
            
            # 移除多余的空行
            markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
        
        return metadata + markdown_content
    
    def _generate_folder_name(self, title: str, platform: str) -> str:
        """生成输出文件夹名称（仅使用标题，不包含来源）"""
        import re
        
        # 清理标题，移除非法字符
        clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
        clean_title = clean_title.strip()
        
        # 移除末尾的来源标识（如"- 小红书"、"- 知乎"等）
        # 匹配模式：" - 平台名称" 或 " - 来源"
        clean_title = re.sub(r'\s*-\s*(小红书|知乎|B站|哔哩哔哩|Reddit|wordpress|网站|社区).*$', '', clean_title)
        clean_title = clean_title.strip()
        
        # 限制长度
        if len(clean_title) > 60:
            clean_title = clean_title[:60]
        
        # 如果标题为空，使用时间戳
        if not clean_title or clean_title == "Untitled":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{platform}_{timestamp}"
        
        return clean_title
    
    def _generate_folder_name_with_llm(self, markdown_content: str, title: str, platform: str, url: str) -> str:
        """
        使用 openai/gpt-oss-20b 模型根据网页内容生成简洁的文件夹名称
        
        Args:
            markdown_content: 保存的 Markdown 内容
            title: 原始页面标题
            platform: 平台名称
            url: 原始 URL
        
        Returns:
            生成的文件夹名称（长度限制在50个字符以内）
        """
        if not GROQ_AVAILABLE:
            logger.warning("Groq SDK 未安装，使用默认文件夹名")
            return self._generate_folder_name(title, platform)
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY 未设置，使用默认文件夹名")
            return self._generate_folder_name(title, platform)
        
        try:
            client = Groq(api_key=api_key)
            
            # 提取内容摘要
            content_lines = markdown_content.split('\n')
            content_start = 0
            
            # 跳过 YAML frontmatter
            if content_lines and content_lines[0].strip() == '---':
                for i, line in enumerate(content_lines[1:], 1):
                    if line.strip() == '---':
                        content_start = i + 1
                        break
            
            # 获取实际内容
            actual_content = '\n'.join(content_lines[content_start:])
            # 移除图片链接
            import re
            actual_content = re.sub(r'!\[.*?\]\(.*?\)', '', actual_content)
            # 限制长度到前800字符
            content_summary = actual_content[:800].strip()
            
            if not content_summary or len(content_summary) < 20:
                logger.warning("内容太短，使用默认文件夹名")
                return self._generate_folder_name(title, platform)
            
            prompt = f"""你是一个专业的文件命名专家，需要根据网页内容生成简洁、语义化的文件夹名称。

## 输入信息

**网页标题**: {title}  
**平台**: {platform}  
**URL**: {url}

**内容摘要**:
{content_summary}

## 命名要求

### 内容要求
1. **核心主题提炼**: 准确捕捉内容的核心概念或关键主题
2. **信息密度**: 在有限字符内传达最大信息量
3. **语义清晰**: 让用户一眼就能理解文件夹内容
4. **区分度高**: 避免使用过于通用的词汇（如"笔记"、"文章"等）

### 格式要求
1. **分隔符**: 使用下划线 `_` 分隔单词，禁止空格或特殊字符
2. **长度限制**: 中文不超过15个字，英文不超过30个字符
3. **字符限制**: 仅使用中文、英文、数字、下划线，禁止 `<>:"/\\|?*`
4. **大小写**: 英文单词首字母大写（如 Python_Best_Practices）
5. **平台名**: 不需要包含平台名称（系统会自动添加）

### 优先级规则
- 如果是教程/指南：突出主题+目标（如 "PyTorch图像分类实战"）
- 如果是问答/讨论：提炼核心问题（如 "如何优化模型推理速度"）
- 如果是工具/资源：强调工具名+用途（如 "Crawl4AI网页抓取"）
- 如果是观点/分析：提炼核心论点（如 "Agent设计五大模式"）

## 优秀示例

- ✅ `PyTorch图像分类实战`（清晰、具体、有操作性）
- ✅ `Agent设计五大模式`（提炼核心数字+主题）
- ✅ `LLM_Token_优化技巧`（技术术语+实用性）
- ❌ `机器学习笔记`（过于笼统）
- ❌ `Python教程第一章`（缺乏语义）
- ❌ `今天看到的文章`（无任何信息价值）

## 输出格式

**仅返回文件夹名称本身**，不要任何解释、引号、序号或其他文字。

文件夹名称："""

            # 使用专门的命名模型
            model_name = os.getenv("GROQ_NAMING_MODEL", "llama-3.1-8b-instant")

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一个文件命名助手，擅长根据网页内容生成简洁、描述性的文件夹名称。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=60,
                temperature=0.3,
            )
            
            folder_name = response.choices[0].message.content.strip()
            
            # 清理文件夹名称
            folder_name = re.sub(r'["\'\'\n\r\t]', '', folder_name)
            folder_name = re.sub(r'[/\\\\]', '_', folder_name)
            folder_name = re.sub(r'[<>:"|?*]', '', folder_name)
            
            # 限制长度
            if len(folder_name) > 50:
                folder_name = folder_name[:50]
            
            # 如果生成失败或为空，使用原始标题
            if not folder_name or len(folder_name) < 3:
                logger.warning("LLM 生成的文件夹名无效，使用原始标题")
                return self._generate_folder_name(title, platform)
            
            logger.info(f"✅ LLM 生成的文件夹名: {folder_name}")
            return folder_name
            
        except Exception as e:
            logger.warning(f"LLM 文件夹命名失败: {e}，使用默认名称")
            return self._generate_folder_name(title, platform)
    

    def _estimate_token_count(self, text: str) -> int:
        """
        估算文本的 token 数量
        规则：
        - 中文字符：1:1 (1个字符 = 1 token)
        - 其他字符（主要是英文）：2:1 (2个字符 = 1 token，即 count / 2)
        """
        import re
        # 统计中文字符数 (基本汉字范围)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', text))
        # 统计其他字符数
        other_chars = len(text) - chinese_chars
        
        # 计算 token
        token_count = chinese_chars + int(other_chars / 2)
        return token_count

    def _generate_report_with_gemini(
        self,
        full_text: str,
        prompt: str
    ) -> Optional[str]:
        """使用 Gemini 生成报告"""
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logger.warning("GEMINI_API_KEY 未设置，无法使用 Gemini 处理长文本")
            return None
            
        if not GEMINI_AVAILABLE:
            logger.warning("Google GenAI SDK 未安装，无法使用 Gemini")
            return None
            
        try:
            model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
            client = genai.Client(api_key=gemini_api_key)
            
            # 使用更详细的提示词
            final_prompt = f"{prompt}\n\n以下是网页归档内容：\n{full_text}"
            
            logger.info(f"使用 Gemini ({model_name}) 生成报告...")
            response = client.models.generate_content(
                model=model_name,
                contents=final_prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini 报告生成失败: {e}")
            return None


    def _generate_report_with_llm(
        self,
        archive_content: str,
        title: str,
        url: str,
        platform: str,
        screenshot_text: str = ""
    ) -> Optional[str]:
        """
        使用 LLM 将网页归档内容转换为结构化报告
        
        Args:
            archive_content: 网页归档原始内容
            title, url, platform: 元信息
            screenshot_text: 截图 OCR 文本 (新增参数)
        """
        if not GROQ_AVAILABLE and not GEMINI_AVAILABLE:
            logger.warning("Generative AI SDK (Groq/Google) 未安装，跳过报告生成")
            return None
        
        # 1. 估算 Token 数量 (包含截图OCR)
        full_context = archive_content
        if screenshot_text:
            full_context += f"\n\n=== 截图 OCR 内容 ===\n{screenshot_text}"

        estimated_tokens = self._estimate_token_count(full_context)
        total_chars = len(full_context)
        logger.info(f"📊 内容估算 tokens: {estimated_tokens:,} ({total_chars:,} 字符)")
        
        # 2. 确定使用的模型
        use_gemini = False
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # 强制使用 Gemini
        if llm_provider == "gemini":
            use_gemini = True
            if not gemini_api_key:
                logger.warning("指定使用 Gemini 但未配置 API Key，将尝试使用 Groq")
                use_gemini = False
                
        # 自动切换：Token > 50000 且未强制指定 OSS
        elif estimated_tokens > 50000 and llm_provider != "oss":
            if gemini_api_key:
                logger.info(f"🔄 文本较长 (>{50000} tokens)，自动切换到 Gemini")
                use_gemini = True
            else:
                logger.warning("文本较长但未配置 Gemini Key，将截断使用 Groq")

        # 3. 使用选定的模型生成报告
        report_content = None
        
        if use_gemini:
             # 使用 Gemini 处理长文本 (提示词 + 全文)
             # 对于 Gemini，我们使用专门的详细提示词
             gemini_prompt = f"""请基于以下网页归档文本(包含截图OCR)，生成一份**极致详细、内容全面**的深度内容概括。

**⚠️ 我们的目标是：生成一份无需阅读原文就能获取所有细节的完整档案。不要在意长度，尽可能多地保留信息。**

**🔍 1. 深度内容解析**
- **逐字逐句的细节保留**：不仅要概括大意，更要还原作者的具体论述逻辑、举例说明、数据支撑。
- **所有关键信息**：任何数字、年份、人名、书名、工具名、代码片段、配置参数，都必须准确记录。
- **不要省略**：不要使用"..."或"略过"等简写，把内容如实写出来。
- **结合截图信息**：利用截图 OCR 内容补充正文中缺失的图表、数据或关键文字。

**⚠️ 2. 识别错误修正与清洗**
- **智能纠错**：根据上下文主动修正 OCR 的同音字错误。
- **屏蔽广告**：完全忽略页面中的广告、推广链接、无关评论。

**📝 3. 输出结构要求**
请按照文章的逻辑结构，将内容划分为多个详细的章节。对于每个章节：
- **小标题**：清晰的主题。
- **详细段落**：使用长段落详细阐述。
- **引用原话**：对于金句或核心观点，请直接引用。

**📊 4. 专项信息提取**
在文末请单独整理：
- **数据汇总**：所有出现的统计数据、价格、参数。
- **知识图谱**：提到的所有概念、理论、法则。
- **行动指南**：如果包含教程，列出一步步的操作指南。

## 输入信息
**标题**: {title}
**来源**: {url}
**平台**: {platform}
"""
             report_content = self._generate_report_with_gemini(
                 full_text=full_context, 
                 prompt=gemini_prompt
             )
        else:
            # 使用 Groq 处理 (可能需要截断)
            groq_api_key = os.getenv("GROQ_API_KEY")
            if not groq_api_key:
                logger.warning("GROQ_API_KEY 未设置，跳过报告生成")
                return None
                
            try:
                client = Groq(api_key=groq_api_key)
                
                # 限制输入长度 (如果未使用 Gemini)
                # Groq 模型通常有 token 限制 (llama-3-70b ~ 128k, 但 output limit 较小)
                # 为了安全起见，如果不使用 Gemini，我们设置一个较大的截断值，而不是之前的 3000
                # 假设主要是中文，30000 字符约 30k tokens，对于 llama-3 来说是安全的 context window
                content_limit = 35000
                final_content = full_context
                
                if len(full_context) > content_limit:
                    logger.warning(f"⚠️  文本过长 ({len(full_context)} 字符)，Groq 模式下截断至 {content_limit} 字符")
                    final_content = full_context[:content_limit] + "\n\n...(内容已截断，建议配置 Gemini 处理长文本)"
                
                # 构建 Groq Prompt
                # 使用 ~~~~ 作为代码块边界，防止内容中包含 ``` 导致 Prompt 截断
                prompt = f"""请将以下网页的归档内容整理成一份**结构化 Markdown 知识档案**。

## 输入信息

**标题**: {title}
**来源**: {url}
**平台**: {platform}

## ⚠️ 重要：识别错误修正与内容清洗

OCR 文本可能存在识别错误，你必须根据上下文**主动识别并修正**：
- **同音字/词错误**: "机器学习"→"鸡器学习"、"Python"→"派森"
- **专业术语**: 使用规范的专业术语
- **屏蔽广告**: 完全忽略广告、推广、导航、评论等无关内容
- **人名地名**: 确保拼写准确
- **标点符号**: 补充缺失的逗号、句号、问号
- **段落分隔**: 修正不合理的换行和分段

## 你需要完成：

1. **结构化组织**
   - 生成清晰的层级标题（##、###）
   - 使用 Markdown 列表格式（有序/无序）
   - 代码块使用 ``` 标记
   - 重要内容使用 **加粗** 或 `行内代码`

2. **信息提炼 (深度详细)**
   - **不要省略细节**：尽可能保留原文的所有关键信息（数据、步骤、代码、参数）
   - **引用原话**：如果作者有核心观点或金句，请直接引用
   - **提取要点**：在文末总结核心结论
   - **结合截图信息**：利用截图 OCR 内容补充正文中缺失的图表、数据或关键文字。

3. **完整性要求**
   - 图片保留原有链接（`![](images/xxx.jpg)`）
   - 链接保留原有格式（`[文本](URL)`）
   - 表格保留原有结构

## 推荐输出结构

# [文章标题]

## 摘要
（50字以内的核心内容概括）

## 主要内容 (详细版)

### [章节1标题]
（详细内容，保留细节...）

### [章节2标题]
（详细内容，保留细节...）

## 关键信息汇总
- 重要数据/参数：...
- 核心观点：...
- 操作步骤：...

## 标签
标签: 标签1, 标签2, 标签3

---

## 原始归档内容

~~~~
{final_content}
~~~~

---

**请直接输出 Markdown 内容，不要任何包裹或额外说明。**"""
                
                # 获取配置的模型
                model = os.getenv("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
                # 使用较大的 token 限制
                max_tokens = int(os.getenv("GROQ_DETAIL_MAX_TOKENS", "12000"))
                temperature = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": """你是一个专业的知识整理专家，具备智能纠错能力。

你的职责是：
- 将混乱的 OCR 文本转换为结构清晰的 Markdown 知识档案
- **智能纠错**：主动识别并修正OCR识别错误（同音字/词、专业术语、标点符号）
- 推断并补全不完整的句子和段落
- 提取核心信息并结构化组织
- 确保输出使用准确、专业的术语表达
- 生成清晰、可长期保存、适合检索的知识文档"""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                
                report_content = response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.warning(f"Groq 报告生成失败: {e}")
                return None
            
        # 4. 检查生成内容有效性
        if not report_content or len(report_content) < 50:
            logger.warning("LLM 生成的报告内容过短，跳过保存")
            return None

        # 检查是否与原始内容完全相同 (LLM 偷懒或Prompt泄露)
        # 简单的去除空白比较，防止 LLM 直接返回原始内容
        if report_content.strip() == archive_content.strip():
            logger.warning("⚠️ LLM 生成内容与原始内容完全相同，视为失败")
            return None

        # 如果生成内容包含大量原始内容的前缀/后缀，也可能是复读机
        if len(report_content) > 100 and (report_content.startswith(archive_content[:100]) or report_content.endswith(archive_content[-100:])):
             # 进一步检查相似度，这里简单处理：如果完全包含则警告
             if archive_content in report_content and len(report_content) < len(archive_content) * 1.2:
                 logger.warning("⚠️ LLM 生成内容疑似复读原始内容，视为失败")
                 # 这种情况下通常是包含 Prompt 中的 ``` 以及原始内容
                 return None
            
        logger.info(f"✅ LLM 生成报告成功（{len(report_content)} 字符）")
        return report_content
    

    def _perform_ocr_on_file(self, image_path: Path) -> str:
        """对单张图片进行 OCR (支持大图分割)"""
        if not image_path.exists():
            return ""
            
        # 尝试从 core 导入大图分割工具
        try:
            from core.image_utils import split_long_image
        except ImportError:
            split_long_image = None
            logger.warning("⚠️  split_long_image utility not found, large images may fail")
        
        try:
            # 优先使用 Vision OCR
            try:
                from ocr.ocr_vision import init_vision_ocr, ocr_image_vision
                ocr = init_vision_ocr(lang="ch", recognition_level="accurate")
                
                # Vision OCR 大图处理逻辑
                processed_text = ""
                
                if split_long_image:
                    try:
                        import tempfile
                        with tempfile.TemporaryDirectory() as temp_chunk_dir:
                            chunk_dir_path = Path(temp_chunk_dir)
                            image_chunks = split_long_image(image_path, output_dir=chunk_dir_path)
                            
                            chunk_texts = []
                            for chunk_path in image_chunks:
                                chunk_text = ocr_image_vision(ocr, str(chunk_path))
                                if chunk_text and chunk_text.strip():
                                    chunk_texts.append(chunk_text.strip())
                            
                            processed_text = "\n\n".join(chunk_texts)
                    except Exception as e:
                        logger.warning(f"⚠️  Image split/OCR (Vision) failed: {e}")
                        processed_text = ocr_image_vision(ocr, str(image_path))
                else:
                    processed_text = ocr_image_vision(ocr, str(image_path))
                
                return processed_text if processed_text else ""
                
            except ImportError:
                # 降级到 PaddleOCR
                try:
                    from ocr.ocr_paddle import init_paddleocr, ocr_image_paddle
                except ImportError:
                    return ""
                
                import logging
                logging.getLogger('ppocr').setLevel(logging.ERROR)
                logging.getLogger('paddle').setLevel(logging.ERROR)
                
                ocr = init_paddleocr(lang="ch", use_gpu=False)
                # PaddingOCR 暂时不支持大图分割逻辑，直接调用 (或后续需补充)
                result = ocr_image_paddle(ocr, str(image_path))
                return result or ""
                
        except Exception as e:
            logger.warning(f"Screenshot OCR failed: {e}")
            return ""

    def _perform_ocr_on_images(self, images_dir: Path) -> str:
        """
        对指定目录中的所有图片进行OCR识别
        
        Args:
            images_dir: 图片目录路径
        
        Returns:
            合并后的OCR文本
        """
        if not images_dir.exists() or not images_dir.is_dir():
            return ""
        
        # 获取所有图片
        image_files = sorted(list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png")) + list(images_dir.glob("*.webp")))
        if not image_files:
            return ""
            
        logger.info(f"🔍 开始识别目录中的 {len(image_files)} 张图片...")
        
        # 尝试从 core 导入大图分割工具
        try:
            from core.image_utils import split_long_image
        except ImportError:
            split_long_image = None
        
        full_text = []

        try:
            # 优先 Vision
            try:
                from ocr.ocr_vision import init_vision_ocr, ocr_image_vision
                ocr = init_vision_ocr(lang="ch", recognition_level="accurate")
                use_vision = True
            except ImportError:
                # Paddle Fallback
                try:
                    from ocr.ocr_paddle import init_paddleocr, ocr_image_paddle
                except ImportError:
                     logger.warning("OCR module missing")
                     return ""
                ocr = init_paddleocr(lang="ch", use_gpu=False)
                use_vision = False
            
            import tempfile
            
            for img_path in image_files:
                try:
                    logger.info(f"   OCR处理: {img_path.name}")
                    if use_vision:
                        # Vision OCR (支持分割)
                        current_text = ""
                        if split_long_image:
                            try:
                                with tempfile.TemporaryDirectory() as temp_chunk_dir:
                                    chunk_dir_path = Path(temp_chunk_dir)
                                    chunks = split_long_image(img_path, output_dir=chunk_dir_path)
                                    
                                    chunk_texts = []
                                    for chunk in chunks:
                                        t = ocr_image_vision(ocr, str(chunk))
                                        if t and t.strip():
                                            chunk_texts.append(t.strip())
                                    current_text = "\n\n".join(chunk_texts)
                            except Exception:
                                current_text = ocr_image_vision(ocr, str(img_path))
                        else:
                             current_text = ocr_image_vision(ocr, str(img_path))
                        
                        if current_text:
                            full_text.append(f"### 图片文本: {img_path.name}\n{current_text}")
                            
                    else:
                        # Paddle OCR (简易模式，暂不分割)
                        t = ocr_image_paddle(ocr, str(img_path))
                        if t:
                             full_text.append(f"### 图片文本: {img_path.name}\n{t}")
                             
                except Exception as e:
                    logger.warning(f"Failed to OCR {img_path.name}: {e}")
                    continue
            
            return "\n\n".join(full_text)
            
        except Exception as e:
            logger.warning(f"OCR directory processing failed: {e}")
            return ""

    
    def close(self):
        """
        关闭归档器
        
        注意：不会关闭浏览器进程，只关闭当前标签页（如果有）
        浏览器会在程序退出时自动关闭
        """
        self._close_tab()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
