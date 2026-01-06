#!/usr/bin/env python3
"""
DrissionPage 浏览器单例管理示例

演示如何在 API 服务或定时任务中使用全局浏览器实例：
- 程序启动时创建一个浏览器实例
- 每个任务使用新标签页
- 任务结束关闭标签页
- 程序退出时关闭浏览器
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.utils.browser_manager import get_browser_manager, cleanup_browser
from archiver.core.drission_crawler import DrissionArchiver
import time


def example_1_basic():
    """
    示例 1: 基础用法 - 单个任务
    """
    print("=" * 60)
    print("示例 1: 基础用法 - 单个任务")
    print("=" * 60)
    
    # 创建归档器（会自动使用全局浏览器管理器）
    archiver = DrissionArchiver(
        output_dir="archived",
        browser_data_dir="./browser_data",
        headless=True
    )
    
    # 归档一个页面
    url = "https://www.zhihu.com/question/123456789"
    result = archiver.archive(url)
    
    print(f"归档结果: {result.get('success')}")
    
    # 关闭归档器（只关闭标签页，不关闭浏览器）
    archiver.close()
    
    print()


def example_2_multiple_tasks():
    """
    示例 2: 多个任务 - 复用浏览器
    """
    print("=" * 60)
    print("示例 2: 多个任务 - 复用浏览器")
    print("=" * 60)
    
    # 创建归档器
    archiver = DrissionArchiver(
        output_dir="archived",
        browser_data_dir="./browser_data",
        headless=True
    )
    
    # 归档多个页面（每个任务一个新标签页）
    urls = [
        "https://www.zhihu.com/question/123456789",
        "https://www.zhihu.com/question/987654321",
        "https://www.zhihu.com/question/111111111",
    ]
    
    for i, url in enumerate(urls, 1):
        print(f"\n任务 {i}/{len(urls)}: {url}")
        result = archiver.archive(url)
        print(f"  结果: {result.get('success')}")
        time.sleep(1)  # 模拟任务间隔
    
    archiver.close()
    print()


def example_3_api_server():
    """
    示例 3: API 服务模式 - 长期运行
    """
    print("=" * 60)
    print("示例 3: API 服务模式 - 长期运行")
    print("=" * 60)
    
    # 模拟 API 服务器接收请求
    class ArchiveAPI:
        def __init__(self):
            # 初始化归档器（全局单例）
            self.archiver = DrissionArchiver(
                output_dir="archived",
                browser_data_dir="./browser_data",
                headless=True
            )
        
        def handle_request(self, url: str):
            """处理单个归档请求"""
            print(f"[API] 收到请求: {url}")
            
            # 每个请求都会使用新标签页，结束后自动关闭
            result = self.archiver.archive(url)
            
            print(f"[API] 处理完成: {result.get('success')}")
            return result
        
        def shutdown(self):
            """关闭服务"""
            self.archiver.close()
    
    # 启动 API 服务
    api = ArchiveAPI()
    
    # 模拟处理多个请求
    requests = [
        "https://www.zhihu.com/question/123456789",
        "https://www.zhihu.com/question/987654321",
    ]
    
    for req in requests:
        api.handle_request(req)
        time.sleep(0.5)
    
    # 服务关闭
    api.shutdown()
    print("[API] 服务已关闭")
    print()


def example_4_direct_browser_access():
    """
    示例 4: 直接使用浏览器管理器
    """
    print("=" * 60)
    print("示例 4: 直接使用浏览器管理器")
    print("=" * 60)
    
    # 获取浏览器管理器
    manager = get_browser_manager()
    
    # 获取全局浏览器实例
    browser = manager.get_browser(
        browser_data_dir="./browser_data",
        headless=True
    )
    
    print(f"浏览器运行状态: {manager.is_alive()}")
    
    # 任务 1
    print("\n任务 1:")
    tab1 = manager.new_tab()
    tab1.get("https://www.zhihu.com")
    print(f"  标题: {tab1.title}")
    manager.close_tab(tab1)
    
    # 任务 2
    print("\n任务 2:")
    tab2 = manager.new_tab()
    tab2.get("https://www.example.com")
    print(f"  标题: {tab2.title}")
    manager.close_tab(tab2)
    
    print(f"\n浏览器运行状态: {manager.is_alive()}")
    print()


def example_5_context_manager():
    """
    示例 5: 使用上下文管理器
    """
    print("=" * 60)
    print("示例 5: 使用上下文管理器")
    print("=" * 60)
    
    # 使用 with 语句自动管理标签页
    with DrissionArchiver(output_dir="archived") as archiver:
        result = archiver.archive("https://www.zhihu.com/question/123456789")
        print(f"归档结果: {result.get('success')}")
    # 退出 with 块时自动关闭标签页
    
    print()


def main():
    """
    主函数：演示所有示例
    """
    print("\n" + "=" * 60)
    print("DrissionPage 浏览器单例管理示例")
    print("=" * 60)
    print()
    print("特性：")
    print("  ✓ 全局单例：整个程序只有一个浏览器实例")
    print("  ✓ 标签页管理：每个任务使用独立标签页")
    print("  ✓ 自动清理：程序退出时自动关闭浏览器")
    print("  ✓ 线程安全：支持多任务并发")
    print()
    
    try:
        # 运行示例（可以选择运行哪些）
        example_1_basic()
        # example_2_multiple_tasks()
        # example_3_api_server()
        # example_4_direct_browser_access()
        # example_5_context_manager()
        
        print("=" * 60)
        print("所有示例运行完成")
        print("=" * 60)
        
    finally:
        # 程序退出时，确保浏览器被关闭
        # 注意：这一步通常由 atexit 自动执行，这里是演示手动调用
        print("\n清理浏览器资源...")
        cleanup_browser()
        print("✓ 浏览器已完全关闭")


if __name__ == "__main__":
    main()
