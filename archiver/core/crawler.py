"""
通用网页归档器
使用 Crawl4AI 实现跨平台网页内容提取
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

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
        cookies: Optional[Dict[str, str]] = None,
        mode: str = "default"
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL
            platform_adapter: 平台适配器（如果为None则自动检测）
            cookies: Cookie字典
            mode: 归档模式 (default/full)
        
        Returns:
            包含归档结果的字典
        """
        logger.info(f"开始归档: {url}")
        
        # 自动检测平台
        if platform_adapter is None:
            platform_name = detect_platform(url)
            
            # 需要登录的平台强制使用 DrissionPage
            if platform_name in ['xiaohongshu', 'twitter']:
                logger.info(f"检测到需要登录的平台 ({platform_name})，强制使用 DrissionPage")
                try:
                    from archiver.core.drission_crawler import DrissionArchiver
                    from archiver.platforms import (
                        ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
                        RedditAdapter, TwitterAdapter, WordPressAdapter
                    )
                    adapters = {
                        "zhihu": ZhihuAdapter(),
                        "xiaohongshu": XiaohongshuAdapter(),
                        "bilibili": BilibiliAdapter(),
                        "reddit": RedditAdapter(),
                        "twitter": TwitterAdapter(),
                        "wordpress": WordPressAdapter(),
                    }
                    platform_adapter_instance = adapters.get(platform_name, WordPressAdapter())
                    
                    drission = DrissionArchiver(
                        output_dir=self.output_dir,
                        browser_data_dir="./browser_data",
                        headless=self.headless,
                        verbose=self.verbose
                    )
                    return drission.archive(url, platform_adapter_instance, mode=mode)
                except Exception as e:
                    logger.error(f"DrissionPage 归档失败: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "url": url
                    }
            from archiver.platforms import (
                ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
                RedditAdapter, TwitterAdapter, WordPressAdapter
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
            
        # 优先使用 DrissionArchiver (因为 Crawl4AI 对 JS 动态渲染支持较弱)
        try:
            from archiver.core.drission_crawler import DrissionArchiver
            drission = DrissionArchiver(
                output_dir=self.output_dir,
                browser_data_dir="./browser_data",
                headless=self.headless,
                verbose=self.verbose
            )
            # 注意: DrissionCrawler 是同步的，这里直接调用
            result = drission.archive(url, platform_adapter, mode=mode)
            if result.get('success'):
                return result
            else:
                logger.warning(f"DrissionPage 归档失败，尝试回退到 Crawl4AI: {result.get('error')}")
        except Exception as e:
            logger.warning(f"DrissionCrawler 异常: {e}")
        
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
            
            # 使用 LLM 生成语义化的文件夹名称并重命名
            logger.info(">> 使用 LLM 生成语义化文件夹名...")
            new_folder_name = self._generate_folder_name_with_llm(
                markdown_content=markdown_content,
                title=page_title,
                platform=platform_adapter.name,
                url=url
            )
            
            # 如果生成的名称与当前文件夹名不同，则重命名
            current_folder_name = folder_path.name
            if new_folder_name != folder_name:
                new_folder_path = self.output_dir / new_folder_name
                try:
                    # 如果目标文件夹已存在，添加时间戳避免冲突
                    if new_folder_path.exists():
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        new_folder_name = f"{new_folder_name}_{timestamp}"
                        new_folder_path = self.output_dir / new_folder_name
                    
                    folder_path.rename(new_folder_path)
                    folder_path = new_folder_path  # 更新引用
                    md_path = folder_path / md_filename
                    logger.info(f"✅ 文件夹已重命名为: {folder_path.name}")
                except Exception as e:
                    logger.warning(f"⚠️  文件夹重命名失败: {e}，保持原名称: {current_folder_name}")
            
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
    
    def _generate_folder_name_with_llm(self, markdown_content: str, title: str, platform: str, url: str) -> str:
        """
        使用 llama-3.1-8b-instant 模型根据网页内容生成简洁的文件夹名称
        
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
            
            # 提取内容摘要（去掉前面的 metadata 和图片链接，限制长度）
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
            
            prompt = f"""根据以下网页内容，生成一个简洁、描述性的文件夹名称。

网页标题：{title}
平台：{platform}
URL：{url}

内容摘要：
{content_summary}

要求：
1. 文件夹名称应该简洁明了，能够反映内容的核心主题
2. 使用下划线(_)分隔单词，不要使用空格或特殊字符
3. 长度不超过30个字符（中文按2个字符计算）
4. 只返回文件夹名称，不要有任何解释或标点符号
5. 使用中文或英文均可，但要确保文件系统兼容
6. 不需要包含平台名称

示例格式：
- 机器学习入门指南
- Python数据分析技巧
- 深度学习图像分类

请直接返回文件夹名称："""

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "你是一个文件命名助手，擅长根据网页内容生成简洁、描述性的文件夹名称。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
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
