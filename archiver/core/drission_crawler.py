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
        """为当前任务创建新标签页"""
        # 获取全局浏览器实例
        browser = self.browser_manager.get_browser(
            browser_data_dir=str(self.browser_data_dir),
            headless=self.headless
        )
        
        # 创建新标签页
        tab = self.browser_manager.new_tab()
        logger.info("✓ 新标签页已创建")
        return tab
    
    def _close_tab(self):
        """关闭当前任务的标签页"""
        if self.current_tab is not None:
            self.browser_manager.close_tab(self.current_tab)
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
        mode: str = "default"
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL（支持分享文本格式，会自动提取URL）
            platform_adapter: 平台适配器（如果为None则自动检测）
            mode: 归档模式 (default/full)
        
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
            
            # 访问页面
            logger.info(f"正在访问: {url}")
            
            # 尝试加载手动配置的 Cookie
            if platform_adapter.name in ['zhihu', 'xiaohongshu', 'bilibili', 'twitter']:
                self._load_manual_cookies(platform_adapter.name, url)
            
            self.current_tab.get(url)
            
            # 智能等待页面加载
            self.current_tab.wait.load_start()
            time.sleep(2)  # 等待 JS 执行
            
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
                            except:
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
                            except:
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
