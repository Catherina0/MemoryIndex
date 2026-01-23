"""
基于 DrissionPage 的网页归档器
使用真实浏览器环境，支持复杂的 JS 渲染和登录态
"""

import os
import time
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
            
            # 确保已访问页面（Cookie 需要域名）
            if not self.current_tab.url or self.current_tab.url == 'about:blank':
                logger.info(f"首次访问页面以设置 Cookie...")
                self.current_tab.get(url)
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
                    self.current_tab.set.cookies({
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
    

    
    def archive(
        self,
        url: str,
        platform_adapter: Optional[PlatformAdapter] = None,
        mode: str = "default",
        generate_report: bool = False,
        with_ocr: bool = False
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL（支持分享文本格式，会自动提取URL）
            platform_adapter: 平台适配器（如果为None则自动检测）
            mode: 归档模式 (default=只提取正文/full=完整内容含评论)
            generate_report: 是否生成 LLM 结构化报告
            with_ocr: 是否对下载的图片进行OCR识别
        
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
            self.current_tab.scroll.to_bottom()
            time.sleep(1)
            self.current_tab.scroll.to_top()
            time.sleep(1)
            
            # 获取页面标题
            page_title = self.current_tab.title
            if not page_title:
                page_title = "Untitled"
            
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
                logger.info(">> 开始OCR识别图片...")
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
                    logger.info("ℹ️  未识别到文字")
            
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
                logger.info(">> 使用 LLM 生成结构化报告...")
                report_content = self._generate_report_with_llm(
                    archive_content=updated_pure_content,
                    title=page_title,
                    url=url,
                    platform=platform_adapter.name
                )
                
                if report_content:
                    report_path = folder_path / "report.md"
                    with open(report_path, "w", encoding="utf-8") as f:
                        f.write(report_content)
                    logger.info(f"✅ 生成结构化报告: {report_path.name}")
            else:
                logger.info("ℹ️  跳过 report.md 生成（使用 --generate-report 启用）")
            
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
                "images_total": len(image_urls) if image_urls else 0,
                "ocr_enabled": with_ocr,
                "ocr_text_length": len(ocr_text) if with_ocr else 0
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
                
                # Manual finding of article to avoid selector issues
                articles = self.current_tab.eles('tag:article')
                article = None
                for a in articles:
                    if a.attrs.get('data-testid') == 'tweet':
                        article = a
                        break
                
                if article:
                    logger.info("  - 找到主推文容器 article[data-testid='tweet']")
                    parts = []
                    parts = []
                    # 1. 提取正文 - Try CSS first, then XPath
                    text_div = article.ele("[data-testid='tweetText']")
                    if not text_div:
                        logger.warning("  - CSS找不tweetText, 尝试XPath...")
                        text_div = article.ele("xpath:.//*[@data-testid='tweetText']")
                    
                    if text_div:
                        parts.append(text_div.html)
                        logger.info(f"  - 找到推文正文 (长度: {len(text_div.text)})")
                    else:
                        logger.warning("  - ❌ 未找到推文正文 [data-testid='tweetText']")
                    
                    # 2. 提取图片容器
                    # Try CSS first, then XPath, then manual scan
                    photos = article.eles("[data-testid='tweetPhoto']")
                    if not photos:
                        logger.info("  - CSS未找到图片, 尝试XPath...")
                        photos = article.eles("xpath:.//*[@data-testid='tweetPhoto']")
                    
                    if photos:
                        logger.info(f"  - 找到 {len(photos)} 个图片容器")
                        for p in photos:
                            html_part = p.html
                            # Ensure high res images in HTML to match downloader logic
                            if 'name=' in html_part:
                                import re
                                html_part = re.sub(r'name=(small|medium|360x360|900x900)', 'name=large', html_part)
                            parts.append(html_part)
                    else:
                        logger.info("  - ❌ 未找到图片容器 (tweetPhoto)")
                        # Fallback: Find all images in article and filter avatars
                        imgs = article.eles("tag:img")
                        valid_imgs = []
                        for img in imgs:
                            src = img.attrs.get('src', '')
                            if 'profile_images' in src or 'emoji' in src:
                                continue
                            if src:
                                # Wrap in simple img tag if container not found
                                valid_imgs.append(f'<img src="{src}" />')
                        
                        if valid_imgs:
                             logger.info(f"  -由于未找到容器，直接提取了 {len(valid_imgs)} 张正文图片")
                             parts.extend(valid_imgs)
                            
                    if parts:
                        combined_html = "\n<br>\n".join(parts)
                        return combined_html
                else:
                    logger.warning("  - ❌ 未找到主推文容器 article[data-testid='tweet']")
                    # DEBUG: Check what articles actually exist
                    arts = self.current_tab.eles('tag:article')
                    logger.info(f"DEBUG: Found {len(arts)} generic articles in Crawler Session")
                    for i, a in enumerate(arts[:3]):
                        logger.info(f"DEBUG Art {i} Attrs: {a.attrs}")
                    
                    # DEBUG: Check title again
                    logger.info(f"DEBUG Page Title: {self.current_tab.title}")

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
                                all_elements = element.eles('tag:div') + element.eles('tag:button')
                                follow_count = 0
                                for elem in all_elements:
                                    if elem.text and elem.text.strip() == '关注':
                                        self.current_tab.run_js("arguments[0].remove()", elem)
                                        follow_count += 1
                                if follow_count > 0:
                                    logger.info(f"  - 已移除 {follow_count} 个关注按钮")
                            except Exception:
                                pass
                    
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

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
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
    
    def _generate_report_with_llm(
        self,
        archive_content: str,
        title: str,
        url: str,
        platform: str
    ) -> Optional[str]:
        """
        使用 LLM 将网页归档内容转换为结构化报告
        
        Args:
            archive_content: 网页归档原始内容（来自 archive_raw.md）
            title: 网页标题
            url: 原始 URL
            platform: 平台名称
        
        Returns:
            生成的 Markdown 报告内容，失败返回 None
        """
        if not GROQ_AVAILABLE:
            logger.warning("Groq SDK 未安装，跳过报告生成")
            return None
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY 未设置，跳过报告生成")
            return None
        
        try:
            client = Groq(api_key=api_key)
            
            # 限制输入长度
            content_limit = 3000
            if len(archive_content) > content_limit:
                archive_content = archive_content[:content_limit] + "\n\n...(内容已截断)"
            
            prompt = f"""请将以下网页的归档内容整理成一份**结构化 Markdown 知识档案**。

## 输入信息

**标题**: {title}
**来源**: {url}
**平台**: {platform}

## ⚠️ 重要：识别错误修正

OCR 文本可能存在识别错误，你必须根据上下文**主动识别并修正**：
- **同音字/词错误**: "机器学习"→"鸡器学习"、"Python"→"派森"
- **专业术语**: 技术名词、学术概念要使用规范表达
- **人名地名**: 确保拼写准确
- **标点符号**: 补充缺失的逗号、句号、问号
- **段落分隔**: 修正不合理的换行和分段

## 你需要完成：

1. **内容清洗与修正**
   - 修正 OCR 识别错误（同音字、错别字、断句问题）
   - 删除无关的广告、推广、导航、评论
   - 补充缺失的标点符号和段落分隔
   - 确保使用专业、准确的术语

2. **结构化组织**
   - 生成清晰的层级标题（##、###）
   - 使用 Markdown 列表格式（有序/无序）
   - 代码块使用 ``` 标记，标注语言
   - 重要内容使用 **加粗** 或 `行内代码`
   - 引用使用 > 格式

3. **信息提炼**
   - 保留所有关键信息（数据、结论、方法、步骤）
   - 删除冗余的口语化表达
   - 如果有作者观点，用「」或 > 引用格式标注
   - 提取核心要点，生成小结

4. **完整性要求**
   - 图片保留原有链接（`![](images/xxx.jpg)`）
   - 链接保留原有格式（`[文本](URL)`）
   - 表格保留原有结构
   - 不要省略重要细节

## 推荐输出结构

# [文章标题]

## 摘要
（50字以内的核心内容概括）

## 主要内容

### [章节1标题]
（详细内容...）

### [章节2标题]
（详细内容...）

## 关键信息
- 重要数据：...
- 核心观点：...
- 操作步骤：...

## 标签
标签: 标签1, 标签2, 标签3

---

## 原始归档内容

```
{archive_content}
```

---

**请直接输出 Markdown 内容，不要任何包裹或额外说明。**"""

            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
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
                max_tokens=8192,
                temperature=0.7,
            )
            
            report_content = response.choices[0].message.content.strip()
            
            if not report_content or len(report_content) < 50:
                logger.warning("LLM 生成的报告内容过短，跳过保存")
                return None
            
            logger.info(f"✅ LLM 生成报告成功（{len(report_content)} 字符）")
            return report_content
            
        except Exception as e:
            logger.warning(f"LLM 报告生成失败: {e}")
            return None
    
    def _perform_ocr_on_images(self, images_dir: Path) -> str:
        """
        对指定目录中的所有图片进行OCR识别
        
        Args:
            images_dir: 图片目录路径
        
        Returns:
            合并后的OCR文本
        """
        if not images_dir.exists() or not images_dir.is_dir():
            logger.warning(f"图片目录不存在: {images_dir}")
            return ""
        
        try:
            # 尝试导入OCR模块
            try:
                from ocr.ocr_vision import init_vision_ocr, ocr_image_vision
                ocr_engine = "vision"
            except ImportError:
                logger.warning("Vision OCR 不可用，尝试使用 PaddleOCR")
                try:
                    from ocr.ocr_paddle import init_paddleocr, ocr_image_paddle
                    ocr_engine = "paddle"
                except ImportError:
                    logger.error("未找到可用的OCR引擎")
                    return ""
            
            # 初始化OCR
            if ocr_engine == "vision":
                ocr = init_vision_ocr(lang="ch", recognition_level="accurate")
                logger.info("使用 Apple Vision OCR")
            else:
                ocr = init_paddleocr(lang="ch", use_gpu=False)
                logger.info("使用 PaddleOCR")
            
            # 获取所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = [
                f for f in images_dir.iterdir() 
                if f.is_file() and f.suffix.lower() in image_extensions
            ]
            
            if not image_files:
                logger.warning(f"在 {images_dir} 中未找到图片文件")
                return ""
            
            logger.info(f"找到 {len(image_files)} 张图片，开始识别...")
            
            # 对每张图片进行OCR
            all_text = []
            for i, image_file in enumerate(image_files, 1):
                try:
                    if ocr_engine == "vision":
                        result = ocr_image_vision(ocr, str(image_file))
                    else:
                        result = ocr_image_paddle(ocr, str(image_file))
                    
                    if result and result.strip():
                        all_text.append(f"## 图片 {i}: {image_file.name}\n\n{result}\n")
                        logger.debug(f"  [{i}/{len(image_files)}] {image_file.name}: {len(result)} 字符")
                    else:
                        logger.debug(f"  [{i}/{len(image_files)}] {image_file.name}: 未识别到文字")
                        
                except Exception as e:
                    logger.warning(f"  [{i}/{len(image_files)}] {image_file.name}: OCR失败 - {e}")
                    continue
            
            if all_text:
                combined_text = "\n\n".join(all_text)
                logger.info(f"✅ OCR完成：共识别 {len(combined_text)} 字符")
                return combined_text
            else:
                logger.warning("所有图片均未识别到文字")
                return ""
                
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
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
