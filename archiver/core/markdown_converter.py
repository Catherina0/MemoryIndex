"""
Markdown 转换器
将HTML内容转换为干净的Markdown格式
"""

import re
from typing import Optional
from datetime import datetime

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False


class MarkdownConverter:
    """HTML到Markdown的转换器"""
    
    def __init__(self):
        """初始化转换器"""
        if HTML2TEXT_AVAILABLE:
            self.h2t = html2text.HTML2Text()
            self.h2t.ignore_links = False
            self.h2t.ignore_images = False
            self.h2t.body_width = 0  # 不自动换行
            self.h2t.single_line_break = False
        else:
            self.h2t = None
    
    def convert(
        self,
        html: str,
        title: str = "",
        url: str = "",
        platform: str = "",
        content_selector: Optional[str] = None,
        exclude_selector: Optional[str] = None
    ) -> str:
        """
        将HTML转换为Markdown
        
        Args:
            html: HTML内容
            title: 页面标题
            url: 源URL
            platform: 平台名称
            content_selector: CSS选择器，用于提取主要内容
            exclude_selector: CSS选择器，用于排除不需要的元素
        
        Returns:
            Markdown格式的内容
        """
        # 清理HTML
        if BS4_AVAILABLE:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 如果指定了内容选择器，提取特定区域
            if content_selector:
                try:
                    selected_content = []
                    for selector in content_selector.split(','):
                        selector = selector.strip()
                        elements = soup.select(selector)
                        if elements:
                            selected_content.extend(elements)
                    
                    if selected_content:
                        # 创建新的soup只包含选中的内容
                        new_soup = BeautifulSoup('<div></div>', 'html.parser')
                        container = new_soup.div
                        for elem in selected_content:
                            container.append(elem)
                        soup = new_soup
                except Exception as e:
                    # 如果选择器解析失败，使用完整HTML
                    pass
            
            # 移除script和style标签
            for tag in soup(['script', 'style', 'noscript']):
                tag.decompose()
            
            # 移除排除选择器指定的元素
            if exclude_selector:
                try:
                    for selector in exclude_selector.split(','):
                        selector = selector.strip()
                        for tag in soup.select(selector):
                            tag.decompose()
                except Exception as e:
                    # 如果选择器解析失败，继续处理
                    pass
            
            html = str(soup)
        
        # 转换为Markdown
        if self.h2t:
            markdown_content = self.h2t.handle(html)
        else:
            # 简单的fallback
            markdown_content = self._simple_html_to_markdown(html)
        
        # 添加元数据头部
        metadata = self._generate_metadata(title, url, platform)
        
        return f"{metadata}\n\n{markdown_content}"
    
    def _generate_metadata(
        self,
        title: str,
        url: str,
        platform: str
    ) -> str:
        """生成Markdown元数据头部"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        metadata = f"""---
title: {title}
url: {url}
platform: {platform}
archived_at: {timestamp}
---
"""
        return metadata
    
    def _simple_html_to_markdown(self, html: str) -> str:
        """简单的HTML到Markdown转换（fallback）"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html)
        # 清理多余空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        return text
    
    def clean_markdown(self, markdown: str) -> str:
        """清理Markdown内容"""
        # 移除多余的空行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # 清理特殊字符
        markdown = markdown.replace('\u200b', '')  # 零宽空格
        
        # 修复图片链接格式
        markdown = re.sub(r'!\s*\[([^\]]*)\]\s*\(([^\)]+)\)', r'![\1](\2)', markdown)
        
        return markdown.strip()
