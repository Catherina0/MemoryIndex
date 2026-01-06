#!/usr/bin/env python3
"""
浏览器单例管理测试脚本
验证浏览器单例的正确性和资源管理
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from archiver.utils.browser_manager import get_browser_manager, cleanup_browser
from archiver.core.drission_crawler import DrissionArchiver
import time


def test_singleton():
    """测试单例模式"""
    print("=" * 60)
    print("测试 1: 单例模式")
    print("=" * 60)
    
    manager1 = get_browser_manager()
    manager2 = get_browser_manager()
    
    assert manager1 is manager2, "❌ 管理器不是单例"
    print("✓ 管理器是单例")
    
    browser1 = manager1.get_browser(headless=True)
    browser2 = manager2.get_browser(headless=True)
    
    assert browser1 is browser2, "❌ 浏览器不是单例"
    print("✓ 浏览器是单例")
    print()


def test_multiple_tabs():
    """测试多标签页管理"""
    print("=" * 60)
    print("测试 2: 多标签页管理")
    print("=" * 60)
    
    manager = get_browser_manager()
    browser = manager.get_browser(headless=True)
    
    # 创建多个标签页
    tabs = []
    for i in range(3):
        tab = manager.new_tab()
        tab.get("https://www.example.com")
        tabs.append(tab)
        print(f"✓ 标签页 {i+1} 已创建: {tab.title}")
    
    # 关闭所有标签页
    for i, tab in enumerate(tabs):
        manager.close_tab(tab)
        print(f"✓ 标签页 {i+1} 已关闭")
    
    print()


def test_archiver_reuse():
    """测试归档器复用浏览器"""
    print("=" * 60)
    print("测试 3: 归档器复用浏览器")
    print("=" * 60)
    
    archiver = DrissionArchiver(
        output_dir="test_archived",
        browser_data_dir="./browser_data_test",
        headless=True
    )
    
    # 模拟多个归档任务
    test_url = "https://www.example.com"
    
    for i in range(3):
        print(f"\n任务 {i+1}:")
        try:
            # 注意：这里使用测试 URL，实际归档可能会失败
            # 但我们主要测试浏览器管理是否正常
            result = archiver.archive(test_url)
            print(f"  归档尝试完成")
        except Exception as e:
            print(f"  预期的错误（测试 URL）: {str(e)[:50]}")
    
    archiver.close()
    print("\n✓ 归档器已关闭（标签页关闭，浏览器保持运行）")
    print()


def test_browser_lifecycle():
    """测试浏览器生命周期"""
    print("=" * 60)
    print("测试 4: 浏览器生命周期")
    print("=" * 60)
    
    manager = get_browser_manager()
    
    # 检查浏览器状态
    print(f"浏览器运行状态: {manager.is_alive()}")
    
    if manager.is_alive():
        print("✓ 浏览器正在运行")
    
    # 创建并关闭标签页
    tab = manager.new_tab()
    tab.get("https://www.example.com")
    print(f"✓ 创建标签页: {tab.title}")
    
    manager.close_tab(tab)
    print("✓ 标签页已关闭")
    
    # 浏览器应该仍在运行
    assert manager.is_alive(), "❌ 浏览器不应该被关闭"
    print("✓ 浏览器仍在运行（正确行为）")
    print()


def test_cleanup():
    """测试清理功能"""
    print("=" * 60)
    print("测试 5: 清理功能")
    print("=" * 60)
    
    manager = get_browser_manager()
    
    # 确保浏览器正在运行
    browser = manager.get_browser(headless=True)
    print(f"浏览器运行状态: {manager.is_alive()}")
    
    # 清理浏览器
    print("执行清理...")
    cleanup_browser()
    
    # 检查浏览器状态
    time.sleep(1)  # 等待清理完成
    print(f"浏览器运行状态: {manager.is_alive()}")
    
    if not manager.is_alive():
        print("✓ 浏览器已成功关闭")
    else:
        print("⚠️  浏览器可能还在运行")
    
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("浏览器单例管理测试")
    print("=" * 60)
    print()
    
    tests = [
        ("单例模式", test_singleton),
        ("多标签页管理", test_multiple_tabs),
        ("归档器复用", test_archiver_reuse),
        ("浏览器生命周期", test_browser_lifecycle),
        ("清理功能", test_cleanup),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {name}")
            print(f"   错误: {e}")
            failed += 1
        
        time.sleep(1)
    
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️  {failed} 个测试失败")
    
    print()


if __name__ == "__main__":
    main()
