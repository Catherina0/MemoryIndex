"""
网页归档功能测试
"""

import unittest
import asyncio
from pathlib import Path
import shutil

from archiver import UniversalArchiver, detect_platform
from archiver.utils.url_parser import normalize_url, is_valid_url, extract_domain
from archiver.platforms import (
    ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
    RedditAdapter, WordPressAdapter
)


class TestURLParser(unittest.TestCase):
    """URL解析器测试"""
    
    def test_detect_platform(self):
        """测试平台检测"""
        # 知乎
        self.assertEqual(detect_platform("https://www.zhihu.com/question/123"), "zhihu")
        
        # 小红书
        self.assertEqual(detect_platform("https://www.xiaohongshu.com/explore/123"), "xiaohongshu")
        
        # B站
        self.assertEqual(detect_platform("https://www.bilibili.com/video/BV123"), "bilibili")
        
        # Reddit
        self.assertEqual(detect_platform("https://www.reddit.com/r/python/"), "reddit")
        
        # 通用
        self.assertEqual(detect_platform("https://example.com/blog/post"), "wordpress")
    
    def test_normalize_url(self):
        """测试URL标准化"""
        # 添加协议
        self.assertEqual(normalize_url("example.com"), "https://example.com")
        
        # 移除尾部斜杠
        self.assertEqual(normalize_url("https://example.com/"), "https://example.com")
        
        # 保留https
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")
    
    def test_extract_domain(self):
        """测试域名提取"""
        self.assertEqual(extract_domain("https://www.example.com/path"), "www.example.com")
        self.assertEqual(extract_domain("https://blog.example.com"), "blog.example.com")
    
    def test_is_valid_url(self):
        """测试URL有效性检查"""
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com/path"))
        self.assertFalse(is_valid_url("not a url"))
        self.assertFalse(is_valid_url(""))


class TestPlatformAdapters(unittest.TestCase):
    """平台适配器测试"""
    
    def test_zhihu_adapter(self):
        """测试知乎适配器"""
        adapter = ZhihuAdapter()
        self.assertEqual(adapter.name, "zhihu")
        self.assertIn("RichContent-inner", adapter.content_selector)
        self.assertIn("Comments-container", adapter.exclude_selector)
    
    def test_xiaohongshu_adapter(self):
        """测试小红书适配器"""
        adapter = XiaohongshuAdapter()
        self.assertEqual(adapter.name, "xiaohongshu")
        self.assertTrue(adapter.requires_login)
    
    def test_bilibili_adapter(self):
        """测试B站适配器"""
        adapter = BilibiliAdapter()
        self.assertEqual(adapter.name, "bilibili")
        self.assertIn("article-holder", adapter.content_selector)
    
    def test_reddit_adapter(self):
        """测试Reddit适配器"""
        adapter = RedditAdapter()
        self.assertEqual(adapter.name, "reddit")
        self.assertIn("shreddit-post", adapter.content_selector)
    
    def test_wordpress_adapter(self):
        """测试WordPress适配器"""
        adapter = WordPressAdapter()
        self.assertEqual(adapter.name, "wordpress")
        self.assertIn("article", adapter.content_selector)


class TestArchiver(unittest.TestCase):
    """归档器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_output_dir = Path("test_archived")
        self.test_output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """测试后清理"""
        if self.test_output_dir.exists():
            shutil.rmtree(self.test_output_dir)
    
    def test_archiver_initialization(self):
        """测试归档器初始化"""
        archiver = UniversalArchiver(output_dir=str(self.test_output_dir))
        self.assertEqual(archiver.output_dir, self.test_output_dir)
        self.assertTrue(archiver.headless)
    
    @unittest.skipUnless(
        # 只在有网络连接且安装了crawl4ai时运行
        False,
        "Skipping integration test - requires network and crawl4ai"
    )
    def test_archive_simple_page(self):
        """测试归档简单页面（集成测试）"""
        async def run_test():
            archiver = UniversalArchiver(output_dir=str(self.test_output_dir))
            result = await archiver.archive("https://example.com")
            self.assertTrue(result['success'])
            self.assertTrue(Path(result['output_path']).exists())
        
        asyncio.run(run_test())


class TestMarkdownConverter(unittest.TestCase):
    """Markdown转换器测试"""
    
    def test_simple_conversion(self):
        """测试简单HTML转换"""
        from archiver.core.markdown_converter import MarkdownConverter
        
        converter = MarkdownConverter()
        html = "<p>Hello <strong>World</strong></p>"
        markdown = converter.convert(html, title="Test", url="https://example.com")
        
        # 检查是否包含元数据
        self.assertIn("title: Test", markdown)
        self.assertIn("url: https://example.com", markdown)
        
        # 检查是否有转换后的内容
        self.assertIn("Hello", markdown)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestURLParser))
    suite.addTests(loader.loadTestsFromTestCase(TestPlatformAdapters))
    suite.addTests(loader.loadTestsFromTestCase(TestArchiver))
    suite.addTests(loader.loadTestsFromTestCase(TestMarkdownConverter))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
