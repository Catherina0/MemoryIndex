"""
基于 DrissionPage 的网页归档器
使用真实浏览器环境，支持复杂的 JS 渲染和登录态
"""

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
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
        
        # 配置浏览器
        self.options = ChromiumOptions()
        self.options.set_user_data_path(str(self.browser_data_dir.absolute()))
        self.options.headless(headless)
        
        # 反爬虫配置
        self.options.set_argument('--no-sandbox')
        self.options.set_argument('--disable-blink-features=AutomationControlled')
        self.options.set_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        
        # 配置 HTML2Text
        self.converter = html2text.HTML2Text()
        self.converter.ignore_links = False
        self.converter.ignore_images = False
        self.converter.body_width = 0
        
        # 浏览器实例（延迟初始化）
        self.page = None
        
        # 配置日志
        if verbose:
            logging.basicConfig(level=logging.INFO)
    
    def _init_browser(self):
        """初始化浏览器实例"""
        if self.page is None:
            logger.info("初始化浏览器...")
            self.page = ChromiumPage(addr_or_opts=self.options)
            logger.info("✓ 浏览器启动成功")
    
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
            
            # 确保已访问页面（Cookie 需要域名）
            if not self.page.url or self.page.url == 'about:blank':
                logger.info(f"首次访问页面以设置 Cookie...")
                self.page.get(url)
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
                
                try:
                    # 设置 Cookie
                    self.page.set.cookies({
                        'name': name,
                        'value': value,
                        'domain': self._get_cookie_domain(url),
                        'path': '/'
                    })
                    logger.debug(f"✓ 设置 Cookie: {name}")
                except Exception as e:
                    logger.warning(f"✗ 设置 Cookie 失败 {name}: {e}")
            
            logger.info(f"✓ 成功加载 {len(cookie_pairs)} 个 Cookie")
            
            # 刷新页面使 Cookie 生效
            logger.info("刷新页面...")
            self.page.refresh()
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
    
    def _close_browser(self):
        """关闭浏览器"""
        if self.page is not None:
            self.page.quit()
            self.page = None
            logger.info("浏览器已关闭")
    
    def archive(
        self,
        url: str,
        platform_adapter: Optional[PlatformAdapter] = None
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL（支持分享文本格式，会自动提取URL）
            platform_adapter: 平台适配器（如果为None则自动检测）
        
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
        
        # 初始化浏览器
        self._init_browser()
        
        try:
            # 自动检测平台
            if platform_adapter is None:
                platform_name = detect_platform(url)
                from archiver.platforms import (
                    ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
                    RedditAdapter, WordPressAdapter
                )
                
                adapters = {
                    "zhihu": ZhihuAdapter(),
                    "xiaohongshu": XiaohongshuAdapter(),
                    "bilibili": BilibiliAdapter(),
                    "reddit": RedditAdapter(),
                    "wordpress": WordPressAdapter(),
                }
                platform_adapter = adapters.get(platform_name, WordPressAdapter())
            
            # 访问页面
            logger.info(f"正在访问: {url}")
            
            # 尝试加载手动配置的 Cookie
            if platform_adapter.name in ['zhihu', 'xiaohongshu', 'bilibili']:
                self._load_manual_cookies(platform_adapter.name, url)
            
            self.page.get(url)
            
            # 智能等待页面加载
            self.page.wait.load_start()
            time.sleep(2)  # 等待 JS 执行
            
            # 滚动页面确保懒加载内容加载完成
            logger.info("滚动页面加载懒加载内容...")
            self.page.scroll.to_bottom()
            time.sleep(1)
            self.page.scroll.to_top()
            time.sleep(1)
            
            # 获取页面标题
            page_title = self.page.title
            if not page_title:
                page_title = "Untitled"
            
            # 提取内容
            content_html = self._extract_content(platform_adapter)
            
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
                platform=platform_adapter.name
            )
            
            # 创建文件夹
            folder_name = self._generate_folder_name(page_title, platform_adapter.name)
            folder_path = self.output_dir / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # 下载图片
            logger.info("开始下载图片...")
            image_downloader = ImageDownloader(
                output_dir=str(folder_path / "images"),
                format="jpg"
            )
            
            # 提取并下载图片
            image_urls = image_downloader.extract_image_urls(content_html, url)
            url_mapping = {}
            if image_urls:
                logger.info(f"发现 {len(image_urls)} 张图片")
                url_mapping = image_downloader.download_all(image_urls, referer=url)
                
                # 更新markdown中的图片链接
                if url_mapping:
                    for orig_url, local_path in url_mapping.items():
                        rel_path = f"images/{local_path}"
                        markdown_content = markdown_content.replace(orig_url, rel_path)
                    logger.info(f"已更新 {len(url_mapping)} 个图片链接")
            
            # 保存 Markdown 文件
            md_filename = "README.md"
            md_path = folder_path / md_filename
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            logger.info(f"归档成功: {folder_path}")
            logger.info(f"  - Markdown: {md_path.name}")
            if image_urls:
                logger.info(f"  - 图片: {len(url_mapping)}/{len(image_urls)} 张")
            
            return {
                "success": True,
                "url": url,
                "platform": platform_adapter.name,
                "output_path": str(folder_path),
                "markdown_path": str(md_path),
                "title": page_title,
                "content_length": len(markdown_content),
                "images_downloaded": len(url_mapping) if image_urls else 0,
                "images_total": len(image_urls) if image_urls else 0
            }
            
        except Exception as e:
            logger.error(f"归档失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }
    
    def _extract_content(self, platform_adapter: PlatformAdapter) -> str:
        """提取页面内容"""
        selector = platform_adapter.content_selector
        
        # 检测是否需要登录（常见登录提示）
        login_indicators = [
            "登录后推荐",
            "马上登录",
            "请先登录",
            "Sign in",
            "Log in",
            "登入"
        ]
        
        page_text = self.page.html
        for indicator in login_indicators:
            if indicator in page_text:
                # 检查是否有实际内容（登录提示通常文本很短）
                if len(self.page.ele('body', timeout=1).text.strip()) < 500:
                    logger.warning(f"⚠️  检测到登录提示: {indicator}")
                    logger.warning("   建议操作：")
                    logger.warning("   1. 运行 'make login' 登录并保存登录态")
                    logger.warning("   2. 或运行 'make config-drission-cookie' 手动配置Cookie")
                    break
        
        # 尝试使用选择器提取内容
        if selector:
            for sel in selector.split(','):
                sel = sel.strip()
                element = self.page.ele(sel, timeout=2)
                if element:
                    html = element.html
                    # 检查是否有实际内容
                    if html and len(html) > 1000:
                        logger.info(f"使用选择器提取内容: {sel}")
                        return html
        
        # 回退：使用通用选择器
        for fallback in ['article', 'main', 'body']:
            element = self.page.ele(fallback, timeout=2)
            if element:
                logger.info(f"使用回退选择器: {fallback}")
                return element.html
        
        # 最后的回退：整个页面
        logger.warning("使用整个页面作为内容")
        return self.page.html
    
    def _convert_to_markdown(
        self,
        html: str,
        title: str,
        url: str,
        platform: str
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
        
        return metadata + markdown_content
    
    def _generate_folder_name(self, title: str, platform: str) -> str:
        """生成输出文件夹名称（平台_标题）"""
        import re
        
        # 清理标题，移除非法字符
        clean_title = re.sub(r'[<>:"/\\|?*]', '', title)
        clean_title = clean_title.strip()
        
        # 限制长度
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        # 如果标题为空，使用时间戳
        if not clean_title or clean_title == "Untitled":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{platform}_{timestamp}"
        
        return f"{platform}_{clean_title}"
    
    def close(self):
        """关闭归档器"""
        self._close_browser()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
