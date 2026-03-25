#!/usr/bin/env python3
"""
统一归档命令行工具 - 自动选择最佳引擎
"""

import sys
import argparse
import subprocess
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
    parser = argparse.ArgumentParser(
        description="通用网页归档工具 - 智能选择引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  %(prog)s "https://www.zhihu.com/question/123456789"
  %(prog)s "https://x.com/user/status/123456789" --mode full
  %(prog)s "https://www.example.com" --visible  # 显示浏览器界面（调试用）
        """
    )
    parser.add_argument('url', help='要归档的 URL 或分享文本')
    parser.add_argument('--mode', choices=['default', 'full'], default='default',
                        help='归档模式：default=只保留正文, full=完整内容（含评论等）')
    parser.add_argument('--generate-report', action='store_true',
                        help='生成 LLM 结构化报告（report.md）')
    parser.add_argument('--screenshot-ocr', action='store_true',
                        help='对全页截图进行 OCR 识别')
    parser.add_argument('--visible', action='store_true',
                        help='显示浏览器界面（默认为无头模式后台运行）')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='输出详细日志')
    
    args = parser.parse_args()
    
    input_text = args.url
    mode = args.mode
    
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
        
        # 默认使用无头模式（后台运行），除非用户指定 --visible
        headless = not args.visible
        
        if args.visible:
            print("👁️  浏览器可见模式（供调试使用）")
        else:
            print("🔒 无头模式（后台运行）")
        print()
        
        with DrissionArchiver(
            output_dir='archived',
            headless=headless,
            verbose=args.verbose or True
        ) as archiver:
            result = archiver.archive(
                url, 
                mode=mode, 
                generate_report=args.generate_report,
                screenshot_ocr=args.screenshot_ocr
            )
            
            if result['success']:
                print(f"\n✓ 归档成功: {result['output_path']}")
                print(f"  平台: {result.get('platform', 'unknown')}")
                print(f"  标题: {result.get('title', 'N/A')}")
                print(f"  图片: {result.get('images_downloaded', 0)}/{result.get('images_total', 0)}")
                print(f"  内容: {result['content_length']} 字符")
                
                # 保存到数据库
                try:
                    from core.archive_processor import ArchiveProcessor
                    processor = ArchiveProcessor()
                    db_id = processor.process_and_save(
                        url=url,
                        output_dir=Path('archived'),
                        archive_result=result,
                        source_type=result.get('platform', 'web_archive'),
                        with_ocr=args.screenshot_ocr,
                        processing_config={
                            'mode': mode,
                            'engine': 'drission'
                        }
                    )
                    print(f"  💾 已保存到数据库 (ID: {db_id})")
                except Exception as e:
                    print(f"  ⚠️  数据库保存失败: {e}")
            else:
                print(f"\n✗ 归档失败: {result.get('error', 'Unknown error')}")
                sys.exit(1)
    else:
        # 使用 Crawl4AI（异步）
        import asyncio
        from archiver import UniversalArchiver
        
        async def archive_with_crawl4ai():
            archiver = UniversalArchiver(output_dir='archived', verbose=True)
            result = await archiver.archive(
                url, 
                mode=mode, 
                generate_report=args.generate_report,
                screenshot_ocr=args.screenshot_ocr
            )
            
            if result['success']:
                print(f"\n✓ 归档成功: {result['output_path']}")
                print(f"  平台: {result['platform']}")
                print(f"  标题: {result['title']}")
                print(f"  内容: {result['content_length']} 字符")
                
                # 保存到数据库
                try:
                    from core.archive_processor import ArchiveProcessor
                    processor = ArchiveProcessor()
                    db_id = processor.process_and_save(
                        url=url,
                        output_dir=Path('archived'),
                        archive_result=result,
                        source_type=result.get('platform', 'web_archive'),
                        with_ocr=args.screenshot_ocr,
                        processing_config={
                            'mode': mode,
                            'engine': 'crawl4ai'
                        }
                    )
                    print(f"  💾 已保存到数据库 (ID: {db_id})")
                except Exception as e:
                    print(f"  ⚠️  数据库保存失败: {e}")
            else:
                print(f"\n✗ 归档失败: {result.get('error', 'Unknown error')}")
                sys.exit(1)
        
        asyncio.run(archive_with_crawl4ai())


def cleanup_temp_chromium():
    """
    清理脚本创建的临时 Chromium 进程
    只关闭使用 temp_file 目录的 Chromium，不影响主 Chrome
    """
    try:
        import time
        # 等待进程完全终止
        time.sleep(1)
        
        # 查找使用 temp_file 目录的 Chromium 进程
        result = subprocess.run(
            ['pgrep', '-f', 'temp_file.*Chromium|temp_file.*chrome'],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    subprocess.run(['kill', '-9', pid], stderr=subprocess.DEVNULL)
                except Exception:
                    pass
            print(f"\n🧹 已清理脚本临时 Chromium 进程 ({len(pids)} 个)")
    except Exception:
        # 如果没有 pgrep 命令（Windows）,忽略
        pass


if __name__ == '__main__':
    try:
        main()
    finally:
        # 清理脚本创建的临时浏览器
        cleanup_temp_chromium()
