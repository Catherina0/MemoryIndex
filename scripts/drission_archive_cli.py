#!/usr/bin/env python3
"""
DrissionPage 归档命令行工具
"""

import sys
from archiver.core.drission_crawler import DrissionArchiver


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("❌ 错误: 请提供URL参数")
        print("用法: python drission_archive_cli.py <URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print(f"🌐 使用 DrissionPage 归档...")
    print(f"📎 输入: {url[:80]}{'...' if len(url) > 80 else ''}\n")
    
    with DrissionArchiver(output_dir='archived', headless=True, verbose=True) as archiver:
        result = archiver.archive(url)
        
        if result['success']:
            print(f"\n✓ 归档成功: {result['output_path']}")
            print(f"  平台: {result.get('platform', 'unknown')}")
            print(f"  标题: {result.get('title', 'N/A')}")
            print(f"  图片: {result.get('images_downloaded', 0)}/{result.get('images_total', 0)}")
            print(f"  内容: {result['content_length']} 字符")
        else:
            print(f"\n✗ 归档失败: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
