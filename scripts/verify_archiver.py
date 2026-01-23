#!/usr/bin/env python3
"""
快速验证归档模块的基础功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    try:
        from archiver import UniversalArchiver, detect_platform
        from archiver.platforms import (
            ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
            RedditAdapter, WordPressAdapter
        )
        from archiver.utils.url_parser import normalize_url, is_valid_url
        from archiver.utils.cookie_manager import CookieManager
        print("  ✓ 所有模块导入成功")
        return True
    except Exception as e:
        print(f"  ✗ 导入失败: {e}")
        return False


def test_url_parser():
    """测试URL解析"""
    print("\n🔍 测试URL解析...")
    from archiver.utils.url_parser import detect_platform, normalize_url, is_valid_url
    
    tests = [
        ("https://www.zhihu.com/question/123", "zhihu"),
        ("https://www.xiaohongshu.com/explore/123", "xiaohongshu"),
        ("https://www.bilibili.com/video/BV123", "bilibili"),
        ("https://www.reddit.com/r/python/", "reddit"),
        ("https://example.com/blog", "wordpress"),
    ]
    
    passed = 0
    for url, expected in tests:
        result = detect_platform(url)
        if result == expected:
            print(f"  ✓ {url[:50]:50s} → {result}")
            passed += 1
        else:
            print(f"  ✗ {url[:50]:50s} → {result} (expected: {expected})")
    
    # 测试URL标准化
    assert normalize_url("example.com") == "https://example.com"
    assert is_valid_url("https://example.com") == True
    print(f"  ✓ URL标准化和验证")
    
    print(f"\n  通过: {passed}/{len(tests)}")
    return passed == len(tests)


def test_platform_adapters():
    """测试平台适配器"""
    print("\n🔍 测试平台适配器...")
    from archiver.platforms import (
        ZhihuAdapter, XiaohongshuAdapter, BilibiliAdapter,
        RedditAdapter, WordPressAdapter
    )
    
    adapters = [
        (ZhihuAdapter(), "zhihu", ".RichContent-inner"),
        (XiaohongshuAdapter(), "xiaohongshu", ".note-content"),
        (BilibiliAdapter(), "bilibili", ".article-holder"),
        (RedditAdapter(), "reddit", "shreddit-post"),
        (WordPressAdapter(), "wordpress", "article"),
    ]
    
    passed = 0
    for adapter, expected_name, expected_selector in adapters:
        if adapter.name == expected_name and expected_selector in adapter.content_selector:
            print(f"  ✓ {expected_name:15s} → selector: {adapter.content_selector[:40]}")
            passed += 1
        else:
            print(f"  ✗ {expected_name:15s} → 配置错误")
    
    print(f"\n  通过: {passed}/{len(adapters)}")
    return passed == len(adapters)


def test_markdown_converter():
    """测试Markdown转换器"""
    print("\n🔍 测试Markdown转换器...")
    try:
        from archiver.core.markdown_converter import MarkdownConverter
        
        converter = MarkdownConverter()
        html = "<p>Hello <strong>World</strong></p>"
        markdown = converter.convert(html, title="Test", url="https://example.com")
        
        assert "title: Test" in markdown
        assert "url: https://example.com" in markdown
        assert "Hello" in markdown
        
        print("  ✓ HTML转Markdown成功")
        print("  ✓ 元数据头部正确")
        return True
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        return False


def test_file_structure():
    """测试文件结构"""
    print("\n🔍 测试文件结构...")
    
    # 获取实际的项目根目录
    # Use relative path for project root
    actual_root = Path(__file__).resolve().parent.parent
    
    required_files = [
        "archiver/__init__.py",
        "archiver/core/__init__.py",
        "archiver/core/crawler.py",
        "archiver/core/markdown_converter.py",
        "archiver/platforms/__init__.py",
        "archiver/platforms/base.py",
        "archiver/platforms/zhihu.py",
        "archiver/platforms/xiaohongshu.py",
        "archiver/platforms/bilibili.py",
        "archiver/platforms/reddit.py",
        "archiver/platforms/wordpress.py",
        "archiver/utils/__init__.py",
        "archiver/utils/url_parser.py",
        "archiver/utils/cookie_manager.py",
        "cli/archive_cli.py",
        "tests/test_archiver.py",
        "docs/ARCHIVER_GUIDE.md",
        "archiver/README.md",
    ]
    
    passed = 0
    for filepath in required_files:
        full_path = actual_root / filepath
        if full_path.exists():
            passed += 1
        else:
            print(f"  ✗ 缺失: {filepath}")
    
    if passed == len(required_files):
        print(f"  ✓ 所有 {len(required_files)} 个必需文件都存在")
        return True
    else:
        print(f"  ⚠️  {passed}/{len(required_files)} 文件存在")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("网页归档模块 - 快速验证")
    print("=" * 60)
    
    results = []
    
    # 运行各项测试
    results.append(("模块导入", test_imports()))
    results.append(("文件结构", test_file_structure()))
    results.append(("URL解析", test_url_parser()))
    results.append(("平台适配器", test_platform_adapters()))
    results.append(("Markdown转换", test_markdown_converter()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\n总计: {total_passed}/{total_tests} 通过")
    
    if total_passed == total_tests:
        print("\n🎉 所有测试通过！归档模块已准备就绪。")
        print("\n下一步:")
        print("  1. 安装依赖: make install")
        print("  2. 查看文档: cat docs/ARCHIVER_GUIDE.md")
        print("  3. 运行示例: python archiver/example.py")
        print("  4. 归档网页: make archive URL=https://example.com")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
