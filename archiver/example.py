"""
网页归档示例脚本
展示如何使用归档功能
"""

import asyncio
from archiver import UniversalArchiver, detect_platform


async def example_single_archive():
    """示例1: 归档单个URL"""
    print("=" * 50)
    print("示例1: 归档单个URL")
    print("=" * 50)
    
    url = "https://example.com"
    
    # 检测平台
    platform = detect_platform(url)
    print(f"检测到平台: {platform}\n")
    
    # 创建归档器
    archiver = UniversalArchiver(
        output_dir="archived",
        verbose=True
    )
    
    # 执行归档
    result = await archiver.archive(url)
    
    if result['success']:
        print(f"\n✓ 归档成功!")
        print(f"  输出路径: {result['output_path']}")
        print(f"  标题: {result['title']}")
        print(f"  平台: {result['platform']}")
        print(f"  内容长度: {result['content_length']} 字符")
    else:
        print(f"\n✗ 归档失败: {result.get('error')}")


async def example_batch_archive():
    """示例2: 批量归档"""
    print("\n" + "=" * 50)
    print("示例2: 批量归档多个URL")
    print("=" * 50)
    
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
    ]
    
    print(f"准备归档 {len(urls)} 个URL...\n")
    
    archiver = UniversalArchiver(
        output_dir="archived",
        verbose=False  # 批量时关闭详细日志
    )
    
    # 批量归档（最多3个并发）
    results = await archiver.archive_batch(urls, max_concurrent=3)
    
    # 统计结果
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    
    print(f"\n归档完成:")
    print(f"  成功: {success_count}/{len(urls)}")
    
    for i, result in enumerate(results):
        if isinstance(result, dict) and result.get('success'):
            print(f"  ✓ {urls[i]}")
        else:
            print(f"  ✗ {urls[i]}")


async def example_platform_specific():
    """示例3: 平台特定归档"""
    print("\n" + "=" * 50)
    print("示例3: 不同平台的归档")
    print("=" * 50)
    
    # 不同平台的URL示例
    platform_urls = {
        "知乎": "https://www.zhihu.com/question/12345/answer/67890",
        "小红书": "https://www.xiaohongshu.com/explore/abc123",
        "B站": "https://www.bilibili.com/read/cv12345678",
        "Reddit": "https://www.reddit.com/r/python/comments/abc123/",
    }
    
    for name, url in platform_urls.items():
        platform = detect_platform(url)
        print(f"{name}: {url}")
        print(f"  → 检测为: {platform}")


async def example_with_cookies():
    """示例4: 使用Cookies归档需要登录的网站"""
    print("\n" + "=" * 50)
    print("示例4: 使用Cookies归档")
    print("=" * 50)
    
    print("对于需要登录的网站，可以使用浏览器Cookies:")
    print("```bash")
    print("python -m cli.archive_cli URL --browser chrome")
    print("```")
    
    # 代码示例
    from archiver.utils.cookie_manager import CookieManager
    
    cookie_manager = CookieManager()
    
    # 从浏览器加载Cookies（需要browser_cookie3）
    # cookies = cookie_manager.load_from_browser("xiaohongshu.com", "chrome")
    
    # 使用Cookies归档
    # archiver = UniversalArchiver()
    # result = await archiver.archive(url, cookies=cookies)


def main():
    """主函数"""
    print("\n🌐 网页归档功能示例\n")
    
    # 运行示例
    try:
        # 示例1: 单个归档
        # asyncio.run(example_single_archive())
        
        # 示例2: 批量归档
        # asyncio.run(example_batch_archive())
        
        # 示例3: 平台检测
        asyncio.run(example_platform_specific())
        
        # 示例4: Cookies使用
        asyncio.run(example_with_cookies())
        
        print("\n" + "=" * 50)
        print("💡 提示：取消注释上面的代码来运行实际的归档示例")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == "__main__":
    main()
