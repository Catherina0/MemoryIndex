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
        mode: str = "default",
        generate_report: bool = False
    ) -> Dict[str, Any]:
        """
        归档指定URL的网页内容
        
        Args:
            url: 目标URL
            platform_adapter: 平台适配器（如果为None则自动检测）
            cookies: Cookie字典
            mode: 归档模式 (default=只提取正文/full=完整内容含评论)
            generate_report: 是否生成 LLM 结构化报告
        
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
            
            # 1. 保存 ocr_raw.md（纯OCR数据，不含元信息）
            ocr_raw_path = folder_path / "ocr_raw.md"
            with open(ocr_raw_path, "w", encoding="utf-8") as f:
                # 更新图片链接后的纯内容
                updated_pure_content = pure_ocr_content
                if url_mapping:
                    for orig_url, local_path in url_mapping.items():
                        rel_path = f"images/{local_path}"
                        updated_pure_content = updated_pure_content.replace(orig_url, rel_path)
                f.write(updated_pure_content)
            logger.info(f"✅ 保存OCR原始数据: {ocr_raw_path.name}")
            
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

详见 [ocr_raw.md](ocr_raw.md)

---

> 💡 **提示**: 使用 `report.md` 查看 LLM 处理后的结构化内容
"""
            
            md_filename = "README.md"
            md_path = folder_path / md_filename
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            logger.info(f"归档成功: {folder_path}")
            logger.info(f"  - README: {md_path.name}")
            logger.info(f"  - OCR原始: {ocr_raw_path.name}")
            if image_urls:
                logger.info(f"  - 图片: {len(url_mapping)}/{len(image_urls)} 张")
            
            # 3. 生成 report.md（仅在需要时）
            if generate_report:
                logger.info(">> 使用 LLM 生成结构化报告...")
                report_content = self._generate_report_with_llm(
                    ocr_content=updated_pure_content,
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
    
    def _generate_report_with_llm(
        self,
        ocr_content: str,
        title: str,
        url: str,
        platform: str
    ) -> Optional[str]:
        """
        使用 LLM 将 OCR 原始数据转换为结构化报告
        
        Args:
            ocr_content: OCR 原始内容（来自 ocr_raw.md）
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
            if len(ocr_content) > content_limit:
                ocr_content = ocr_content[:content_limit] + "\n\n...(内容已截断)"
            
            prompt = f"""请将以下网页的 OCR 提取内容整理成一份**结构化 Markdown 知识档案**。

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

## OCR 原始内容

```
{ocr_content}
```

---

**请直接输出 Markdown 内容，不要任何包裹或额外说明。**"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
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
