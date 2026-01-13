"""
网页归档命令行工具
"""

import asyncio
import argparse
import sys
from pathlib import Path
import logging

from archiver import UniversalArchiver, detect_platform
from archiver.utils.cookie_manager import CookieManager
from archiver.utils.url_parser import extract_url_from_text, extract_domain


def setup_logging(verbose: bool):
    """配置日志"""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def archive_single(args):
    """归档单个URL"""
    # 从输入文本中提取URL（支持分享文本格式）
    url = extract_url_from_text(args.url)
    if not url:
        print(f"❌ 错误：无法从输入中提取有效的URL")
        print(f"   输入内容: {args.url}")
        sys.exit(1)
    
    # 如果提取的URL与输入不同，提示用户
    if url != args.url:
        print(f"📎 从分享文本中提取URL: {url}\n")
    
    archiver = UniversalArchiver(
        output_dir=args.output,
        headless=not args.show_browser,
        verbose=args.verbose
    )
    
    # 处理Cookies
    cookies = None
    if args.cookies:
        cookie_manager = CookieManager()
        if args.browser:
            domain = extract_domain(url)
            cookies = cookie_manager.load_from_browser(domain, args.browser)
        else:
            cookies = cookie_manager.load_from_file(args.cookies)
    
    # 注意：对于小红书，不需要手动指定，爬虫会自动加载XHS配置
    
    # 执行归档
    result = await archiver.archive(url, cookies=cookies)
    
    if result['success']:
        print(f"✓ 归档成功: {result['output_path']}")
        print(f"  平台: {result['platform']}")
        print(f"  标题: {result['title']}")
        print(f"  内容长度: {result['content_length']} 字符")
    else:
        print(f"✗ 归档失败: {result.get('error', 'Unknown error')}")
        sys.exit(1)


async def archive_batch(args):
    """批量归档多个URL"""
    # 从文件读取URL列表
    with open(args.file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"准备归档 {len(urls)} 个URL...")
    
    archiver = UniversalArchiver(
        output_dir=args.output,
        headless=not args.show_browser,
        verbose=args.verbose
    )
    
    results = await archiver.archive_batch(urls, max_concurrent=args.concurrent)
    
    # 统计结果
    success_count = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    failed_count = len(results) - success_count
    
    print(f"\n归档完成:")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    
    # 显示失败的URL
    if failed_count > 0:
        print("\n失败的URL:")
        for i, result in enumerate(results):
            if isinstance(result, Exception) or (isinstance(result, dict) and not result.get('success')):
                print(f"  - {urls[i]}")


def archive_command(args):
    """供 memidx 子命令调用的简化封装。

    main_cli 中的 `memidx archive` 目前只支持：
      memidx archive URL [--output DIR]

    这里直接复用本文件的 archive_single 逻辑，
    使用无头浏览器、无 Cookie、默认并发等配置。
    """
    # 构造与本模块预期兼容的参数对象
    class SimpleArgs:
        pass

    simple = SimpleArgs()
    simple.url = args.url
    simple.output = args.output or 'archived'
    simple.show_browser = False
    simple.verbose = False
    simple.cookies = None
    simple.browser = None

    # 运行单 URL 归档
    setup_logging(simple.verbose)
    try:
        asyncio.run(archive_single(simple))
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='网页归档工具 - 将网页内容保存为Markdown格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 归档单个URL
  python -m cli.archive_cli https://www.zhihu.com/question/123456/answer/789012
  
  # 指定输出目录
  python -m cli.archive_cli https://example.com -o my_archives
  
  # 批量归档（从文件读取URL列表）
  python -m cli.archive_cli -f urls.txt
  
  # 使用浏览器Cookies（需要browser_cookie3）
  python -m cli.archive_cli https://example.com --browser chrome
  
  # 显示浏览器窗口（调试用）
  python -m cli.archive_cli https://example.com --show-browser -v
        """
    )
    parser.add_argument('--version', action='version', version='memoryindex 1.0.4')
    
    # 基本参数
    parser.add_argument('url', nargs='?', help='要归档的URL')
    parser.add_argument('-f', '--file', help='包含URL列表的文件（每行一个URL）')
    parser.add_argument('-o', '--output', default='archived', help='输出目录（默认: archived）')
    
    # Cookie相关
    parser.add_argument('--cookies', help='Cookie文件路径')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'edge', 'safari'],
                       help='从浏览器加载Cookies')
    
    # 高级选项
    parser.add_argument('--show-browser', action='store_true',
                       help='显示浏览器窗口（非无头模式）')
    parser.add_argument('-c', '--concurrent', type=int, default=3,
                       help='批量归档时的并发数（默认: 3）')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细日志')
    
    # 平台检测
    parser.add_argument('--detect', action='store_true',
                       help='仅检测URL所属平台，不执行归档')
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.verbose)
    
    # 检查参数
    if not args.url and not args.file:
        parser.print_help()
        sys.exit(1)
    
    # 平台检测模式
    if args.detect and args.url:
        platform = detect_platform(args.url)
        print(f"检测到平台: {platform}")
        sys.exit(0)
    
    # 执行归档
    try:
        if args.file:
            asyncio.run(archive_batch(args))
        else:
            asyncio.run(archive_single(args))
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n错误: {e}")
        if args.verbose:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()
