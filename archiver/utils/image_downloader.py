"""
图片下载器
用于下载网页中的图片并保存为本地文件
"""

import os
import re
import logging
import hashlib
import base64
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests not installed. Run: pip install requests")

try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logging.warning("Pillow not installed. Run: pip install pillow")


logger = logging.getLogger(__name__)


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, output_dir: str, format: str = "jpg"):
        """
        初始化图片下载器
        
        Args:
            output_dir: 图片保存目录
            format: 图片格式 (jpg, png, webp等)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.format = format.lower()
        self.downloaded_images = {}  # URL -> 本地路径映射
        
    def extract_image_urls(self, html: str, base_url: str) -> List[str]:
        """
        从HTML中提取所有图片URL（包括base64）
        
        Args:
            html: HTML内容
            base_url: 基础URL，用于转换相对路径
        
        Returns:
            图片URL列表（包括data: URL）
        """
        # 先解码 HTML 实体
        import html as html_module
        html = html_module.unescape(html)
        
        # 匹配 img src 和 data-src 属性
        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+data-src=["\']([^"\']+)["\']',
            r'<img[^>]+data-original=["\']([^"\']+)["\']',
            # 🆕 推特的背景图片
            r'background-image:\s*url\(["\']?([^"\'()]+)["\']?\)',
        ]
        
        urls = set()
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for url in matches:
                # 再次检查和清理 URL
                url = url.strip()
                
                # 过滤无效 URL（包含引号、不完整的 URL 等）
                if '"' in url or "'" in url:
                    # 提取引号之间的内容
                    clean_match = re.search(r'https?://[^"\' ]+', url)
                    if clean_match:
                        url = clean_match.group(0)
                    else:
                        continue  # 跳过无效 URL
                
                # 处理 data URL（base64 图片）
                if url.startswith('data:'):
                    urls.add(url)
                    continue
                
                # 转换为绝对URL
                abs_url = urljoin(base_url, url)
                # 只处理http/https图片
                if abs_url.startswith(('http://', 'https://')):
                    # 🆕 推特图片特殊处理：确保使用large尺寸
                    if 'twimg.com' in abs_url:
                        # 对于profile图片（头像），保持原尺寸，不强制large
                        if 'profile_images' in abs_url:
                            # 移除我们添加的format和name参数
                            if '?format=jpg&name=large' in abs_url:
                                abs_url = abs_url.replace('?format=jpg&name=large', '')
                        # 对于媒体图片，确保使用large尺寸
                        elif '/media/' in abs_url:
                            if 'name=' in abs_url:
                                abs_url = re.sub(r'name=\w+', 'name=large', abs_url)
                            elif '?' not in abs_url:
                                abs_url += '?format=jpg&name=large'
                    urls.add(abs_url)
        
        logger.info(f"提取到 {len(urls)} 个图片URL")
        return list(urls)
    
    def download_image(
        self,
        url: str,
        filename: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        referer: Optional[str] = None
    ) -> Optional[str]:
        """（支持HTTP和base64）
        
        Args:
            url: 图片URL（HTTP或data: URL）
            filename: 保存文件名（不含扩展名）
            headers: 请求头
            referer: Referer URL（用于防盗链）
        
        Returns:
            本地文件路径，失败返回None
        """
        # 检查缓存
        if url in self.downloaded_images:
            logger.debug(f"使用缓存的图片: {url[:50]}...")
            return self.downloaded_images[url]
        
        try:
            # 生成文件名
            if not filename:
                # 使用URL的哈希值作为文件名
                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                filename = f"image_{url_hash}"
            
            # 处理 base64 图片
            if url.startswith('data:'):
                return self._save_base64_image(url, filename)
            
            # 处理 HTTP 图片
            if not REQUESTS_AVAILABLE:
                logger.error("requests not installed")
                return None
            
            # 设置请求头
            if not headers:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                }
            
            # 设置Referer（防止防盗链）
            # 注意：Referer 必须是 ASCII 编码，避免中文字符
            if referer:
                # 确保 referer 不包含中文字符
                try:
                    referer.encode('latin-1')
                    headers['Referer'] = referer
                except UnicodeEncodeError:
                    # 如果包含中文，使用域名作为 referer
                    from urllib.parse import urlparse
                    parsed = urlparse(referer)
                    headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
            elif 'xiaohongshu' in url or 'xhscdn' in url:
                headers['Referer'] = 'https://www.xiaohongshu.com/'
            elif 'zhihu' in url or 'zhimg' in url:
                headers['Referer'] = 'https://www.zhihu.com/'
            else:
                # 从 URL 中提取域名作为 referer
                from urllib.parse import urlparse
                parsed = urlparse(url)
                headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
            
            # 下载图片
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 保存图片
            return self._save_image_data(response.content, filename)
            
        except Exception as e:
            logger.error(f"下载图片失败 {url[:80]}...: {e}")
            return None
    
    def _save_base64_image(self, data_url: str, filename: str) -> Optional[str]:
        """
        保存 base64 编码的图片
        
        Args:
            data_url: data: URL (如 data:image/png;base64,...)
            filename: 文件名（不含扩展名）
        
        Returns:
            本地文件路径，失败返回None
        """
        try:
            # 解析 data URL
            # 格式: data:image/png;base64,iVBORw0KGgo...
            match = re.match(r'data:image/([^;]+);base64,(.+)', data_url)
            if not match:
                logger.error(f"无效的 data URL 格式")
                return None
            
            image_format = match.group(1)  # png, jpeg, etc.
            base64_data = match.group(2)
            
            # 解码 base64
            image_data = base64.b64decode(base64_data)
            
            # 保存图片
            local_path = self._save_image_data(image_data, filename, hint_format=image_format)
            
            if local_path:
                # 缓存结果
                self.downloaded_images[data_url] = local_path
                logger.info(f"成功保存 base64 图片: {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"保存 base64 图片失败: {e}")
            return None
    
    def _save_image_data(
        self,
        image_data: bytes,
        filename: str,
        hint_format: Optional[str] = None
    ) -> Optional[str]:
        """
        保存图片数据到文件
        
        Args:
            image_data: 图片二进制数据
            filename: 文件名（不含扩展名）
            hint_format: 提示的图片格式（用于 base64）
        
        Returns:
            本地文件路径，失败返回None
        """
        try:
            # 处理图片
            if PIL_AVAILABLE:
                try:
                    # 使用PIL转换格式
                    img = Image.open(BytesIO(image_data))
                    
                    # 转换为RGB模式（如果是RGBA）
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img
                    
                    # 确保是RGB模式
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # 保存
                    output_path = self.output_dir / f"{filename}.{self.format}"
                    # JPEG格式不支持透明度，必须是RGB
                    save_format = 'JPEG' if self.format.lower() in ('jpg', 'jpeg') else self.format.upper()
                    img.save(output_path, save_format, quality=90)
                    
                except Exception as e:
                    logger.debug(f"PIL处理图片失败: {e}，尝试直接保存")
                    # fallback: 直接保存
                    ext = hint_format or self.format
                    output_path = self.output_dir / f"{filename}.{ext}"
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                
            else:
                # 直接保存原始内容
                ext = hint_format or self.format
                output_path = self.output_dir / f"{filename}.{ext}"
                with open(output_path, 'wb') as f:
                    f.write(image_data)
            
            return str(output_path.name)  # 只返回文件名
            
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None
    
    def download_all(
        self,
        urls: List[str],
        headers: Optional[Dict[str, str]] = None,
        referer: Optional[str] = None
    ) -> Dict[str, str]:
        """
        批量下载图片
        
        Args:
            urls: 图片URL列表
            headers: 请求头
            referer: Referer URL
        
        Returns:
            URL到本地路径的映射字典
        """
        results = {}
        for i, url in enumerate(urls, 1):
            logger.info(f"下载图片 {i}/{len(urls)}")
            local_path = self.download_image(url, headers=headers, referer=referer)
            if local_path:
                results[url] = local_path
        
        logger.info(f"成功下载 {len(results)}/{len(urls)} 张图片")
        return results
    
    def replace_markdown_images(
        self,
        markdown: str,
        url_mapping: Dict[str, str]
    ) -> str:
        """
        替换Markdown中的图片链接为本地路径
        
        Args:
            markdown: Markdown内容
            url_mapping: URL到本地路径的映射
        
        Returns:
            替换后的Markdown
        """
        for url, local_path in url_mapping.items():
            # 替换各种格式的图片引用
            markdown = markdown.replace(url, local_path)
            markdown = markdown.replace(f'({url})', f'({local_path})')
            markdown = markdown.replace(f']({url})', f']({local_path})')
        
        return markdown
