#!/usr/bin/env python3
"""
统一归档命令行工具 - 自动选择最佳引擎
"""

import sys
from pathlib import Path
from archiver.utils.url_parser import extract_url_from_text, detect_platform


def should_use_drissionpage(platform: str) -> bool:
    """
    根据平台和配置决定使用哪个引擎
    
    规则：
    1. 小红书 → 强制 DrissionPage（JS渲染 + 反爬严格）
    2. 知乎、B站 → 优先 DrissionPage（如果有登录态或手动cookie）
    3. 其他平台 → Crawl4AI（快速）
    """
    # 小红书强制使用 DrissionPage
    if platform == 'xiaohongshu':
        return True
    
    # 检查是否有手动配置的 Cookie
    cookie_file = Path(f"archiver/config/{platform}_drission_cookie.txt")
    if cookie_file.exists() and cookie_file.stat().st_size > 0:
        return True
    
    # 检查是否有 browser_data（登录态）
    browser_data = Path('browser_data/Default/Cookies')
    if browser_data.exists() and browser_data.stat().st_size > 1000:
        # 如果是需要登录的平台且有登录态，使用 DrissionPage
        if platform in ['zhihu', 'bilibili']:
            return True
    
    # 默认使用 Crawl4AI（更快）
    return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("❌ 错误: 请提供URL参数")
        print("用法: python unified_archive_cli.py <URL>")
        print("\n💡 支持分享文本格式，会自动提取URL")
        sys.exit(1)
    
    input_text = sys.argv[1]
    
    # 解析模式参数
    mode = "default"
    for arg in sys.argv:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1]
    
    # 提取 URL
    url = extract_url_from_text(input_text)
    if not url:
        print(f"❌ 错误：无法从输入中提取有效的URL")
        print(f"   输入内容: {input_text}")
        sys.exit(1)
    
    # 如果提取的URL与输入不同，提示用户
    if url != input_text:
        print(f"📎 从分享文本中提取URL: {url}\n")
    
    # 检测平台
    platform = detect_platform(url)
    print(f"🔍 检测平台: {platform}")
    
    # 决定使用哪个引擎
    use_drission = should_use_drissionpage(platform)
    engine = "DrissionPage" if use_drission else "Crawl4AI"
    print(f"⚙️  选择引擎: {engine}")
    print()
    
    # 执行归档
    if use_drission:
        # 使用 DrissionPage（真实浏览器）
        from archiver.core.drission_crawler import DrissionArchiver
        
        with DrissionArchiver(output_dir='archived', headless=True, verbose=True) as archiver:
            result = archiver.archive(url, mode=mode)
            
            if result['success']:
                print(f"\n✓ 归档成功: {result['output_path']}")
                print(f"  平台: {result.get('platform', 'unknown')}")
                print(f"  标题: {result.get('title', 'N/A')}")
                print(f"  图片: {result.get('images_downloaded', 0)}/{result.get('images_total', 0)}")
                print(f"  内容: {result['content_length']} 字符")
            else:
                print(f"\n✗ 归档失败: {result.get('error', 'Unknown error')}")
                sys.exit(1)
    else:
        # 使用 Crawl4AI（异步）
        import asyncio
        from archiver import UniversalArchiver
        
        async def archive_with_crawl4ai():
            archiver = UniversalArchiver(output_dir='archived', verbose=True)
            result = await archiver.archive(url, mode=mode)
            
            if result['success']:
                print(f"\n✓ 归档成功: {result['output_path']}")
                print(f"  平台: {result['platform']}")
                print(f"  标题: {result['title']}")
                print(f"  内容: {result['content_length']} 字符")
            else:
                print(f"\n✗ 归档失败: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        asyncio.run(archive_with_crawl4ai())


if __name__ == '__main__':
    main()
