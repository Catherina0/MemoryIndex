"""
通用网页归档器
使用 Crawl4AI 实现跨平台网页内容提取
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logging.warning("Crawl4AI not installed. Run: pip install crawl4ai")

from archiver.platforms.base import PlatformAdapter
from archiver.utils.url_parser import detect_platform
from archiver.core.markdown_converter import MarkdownConverter
from archiver.utils.image_downloader import ImageDownloader


logger = logging.getLogger(__name__)


class UniversalArchiver:
    """通用网页归档器"""
    
    def __init__(
        self,
        output_dir: str = "archived",
        headless: bool = True,
        verbose: bool = False
    ):
        """
        初始化归档器
        
        Args:
            output_dir: 输出目录
            headless: 是否使用无头模式
            verbose: 是否输出详细日志
        """
        if not CRAWL4AI_AVAILABLE:
            raise ImportError("Please install crawl4ai: pip install crawl4ai")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.headless = headless
        self.verbose = verbose
        self.markdown_converter = MarkdownConverter()
        
        # 配置日志
        if verbose:
            logging.basicConfig(level=logging.INFO)
    
    async def archive(
        self,
        url: str,
        platform_adapter: Optional[PlatformAdapter] = None,
        cookies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL
            platform_adapter: 平台适配器（如果为None则自动检测）
            cookies: Cookie字典
        
        Returns:
            包含归档结果的字典
        """
        logger.info(f"开始归档: {url}")
        
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
        
        # 自动获取小红书Cookie（如果需要）
        if platform_adapter.name == "xiaohongshu" and cookies is None:
            logger.info("检测到小红书平台，尝试自动加载Cookie...")
            from archiver.utils.cookie_manager import get_xiaohongshu_cookies
            cookies = get_xiaohongshu_cookies()
            if cookies:
                logger.info("✓ 成功加载小红书Cookie")
            else:
                logger.warning("⚠️  未找到小红书Cookie，可能无法访问需要登录的内容")
                logger.info("提示：运行 'make config-xhs-cookie' 配置Cookie")
        
        # 自动获取知乎Cookie（如果需要）
        if platform_adapter.name == "zhihu" and cookies is None:
            logger.info("检测到知乎平台，尝试自动加载Cookie...")
            from archiver.utils.cookie_manager import get_zhihu_cookies
            cookies = get_zhihu_cookies()
            if cookies:
                logger.info("✓ 成功加载知乎Cookie")
            else:
                logger.warning("⚠️  未找到知乎Cookie，可能无法访问需要登录的内容")
                logger.info("提示：请先在Chrome浏览器登录知乎，程序将自动读取Cookie")
        
        # 将cookies字典转换为Playwright格式（列表）
        playwright_cookies = None
        if cookies:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            playwright_cookies = []
            for name, value in cookies.items():
                cookie = {
                    'name': name,
                    'value': value,
                    'domain': domain if not domain.startswith('www.') else domain[4:],
                    'path': '/',
                }
                playwright_cookies.append(cookie)
            
            logger.info(f"转换了 {len(playwright_cookies)} 个 Cookie")
        
        # 配置浏览器
        browser_config = BrowserConfig(
            headless=self.headless,
            verbose=self.verbose,
            cookies=playwright_cookies,
            extra_args=["--disable-blink-features=AutomationControlled"]
        )
        
        # 配置爬虫运行参数
        run_config = CrawlerRunConfig(
            wait_until="networkidle",
            page_timeout=30000,
        )
        
        # 执行爬取
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(
                url=url,
                config=run_config
            )
            
            if not result.success:
                logger.error(f"爬取失败: {result.error_message}")
                return {
                    "success": False,
                    "error": result.error_message,
                    "url": url
                }
            
            # 转换为Markdown
            page_title = result.metadata.get("title", "Untitled")
            markdown_content = self.markdown_converter.convert(
                html=result.html,
                title=page_title,
                url=url,
                platform=platform_adapter.name,
                content_selector=platform_adapter.content_selector,
                exclude_selector=platform_adapter.exclude_selector
            )
            
            # 创建文件夹（平台_标题）
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
            image_urls = image_downloader.extract_image_urls(result.html, url)
            if image_urls:
                logger.info(f"发现 {len(image_urls)} 张图片")
                url_mapping = image_downloader.download_all(image_urls, referer=url)
                
                # 更新markdown中的图片链接
                if url_mapping:
                    for orig_url, local_path in url_mapping.items():
                        # 使用相对路径 images/xxx.jpg
                        rel_path = f"images/{local_path}"
                        markdown_content = markdown_content.replace(orig_url, rel_path)
                    logger.info(f"已更新 {len(url_mapping)} 个图片链接")
            
            # 保存markdown文件
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
    
    def _generate_filename(self, url: str, platform: str) -> str:
        """生成输出文件名（旧版方法，保留兼容性）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 从URL中提取简短标识
        url_hash = abs(hash(url)) % 10000
        return f"{platform}_{url_hash}_{timestamp}.md"
    
    def _generate_folder_name(self, title: str, platform: str) -> str:
        """生成输出文件夹名称（平台_标题）"""
        # 清理标题，移除非法字符
        import re
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
    
    async def archive_batch(
        self,
        urls: list,
        max_concurrent: int = 3
    ) -> list:
        """
        批量归档多个URL
        
        Args:
            urls: URL列表
            max_concurrent: 最大并发数
        
        Returns:
            归档结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def archive_with_semaphore(url):
            async with semaphore:
                return await self.archive(url)
        
        tasks = [archive_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results


async def archive_url(url: str, output_dir: str = "archived") -> Dict[str, Any]:
    """
    简单的单URL归档函数
    
    Args:
        url: 目标URL
        output_dir: 输出目录
    
    Returns:
        归档结果
    """
    archiver = UniversalArchiver(output_dir=output_dir)
    return await archiver.archive(url)
