#!/usr/bin/env python3
"""
项目清理工具
清理临时文件、debug文件和无用数据，使项目更加工程化
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def cleanup_debug_files():
    """清理 debug 文件"""
    print("🧹 清理 Debug 文件...")
    
    debug_files = [
        "debug_chromium_404.py",
        "debug_drission.py",
        "debug_exact_config.py",
        "debug_manual_chrome.py",
    ]
    
    removed = []
    for filename in debug_files:
        file_path = PROJECT_ROOT / filename
        if file_path.exists():
            file_path.unlink()
            removed.append(filename)
            print(f"   ✅ 删除: {filename}")
    
    if not removed:
        print("   ℹ️  无 debug 文件需要清理")
    
    return len(removed)


def cleanup_test_files():
    """清理根目录的临时测试文件（保留 tests/ 目录）"""
    print("\n🧹 清理临时测试文件...")
    
    test_files = [
        "test_browser_launch.py",
        "test_browser_simple.py",
        "test_chromium_launch.py",
        "test_find_browser.py",
        "test_twitter_extract.py",
    ]
    
    removed = []
    for filename in test_files:
        file_path = PROJECT_ROOT / filename
        if file_path.exists():
            file_path.unlink()
            removed.append(filename)
            print(f"   ✅ 删除: {filename}")
    
    if not removed:
        print("   ℹ️  无临时测试文件需要清理")
    
    return len(removed)


def cleanup_browser_data():
    """清理临时浏览器数据（保留主 browser_data）"""
    print("\n🧹 清理临时浏览器数据...")
    
    dirs_to_remove = [
        "browser_data_debug",
        "browser_data_test",
    ]
    
    removed = []
    total_size = 0
    
    for dirname in dirs_to_remove:
        dir_path = PROJECT_ROOT / dirname
        if dir_path.exists():
            # 计算大小
            size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            
            shutil.rmtree(dir_path)
            removed.append(dirname)
            total_size += size_mb
            print(f"   ✅ 删除: {dirname} ({size_mb:.1f} MB)")
    
    if not removed:
        print("   ℹ️  无临时浏览器数据需要清理")
    
    return len(removed), total_size


def cleanup_temp_dirs():
    """清理临时目录"""
    print("\n🧹 清理临时目录...")
    
    dirs_to_remove = [
        "temp_xhs",
        "test_archived",
        "test_images",
    ]
    
    removed = []
    total_size = 0
    
    for dirname in dirs_to_remove:
        dir_path = PROJECT_ROOT / dirname
        if dir_path.exists() and list(dir_path.iterdir()):  # 只清理非空目录
            # 计算大小
            size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
            size_mb = size / (1024 * 1024)
            
            shutil.rmtree(dir_path)
            removed.append(dirname)
            total_size += size_mb
            print(f"   ✅ 删除: {dirname} ({size_mb:.1f} MB)")
        elif dir_path.exists():
            print(f"   ℹ️  跳过空目录: {dirname}")
    
    if not removed:
        print("   ℹ️  无临时目录需要清理")
    
    return len(removed), total_size


def cleanup_archived_debug():
    """清理 archived 目录中的 debug 文件"""
    print("\n🧹 清理归档目录中的 debug 文件...")
    
    archived_dir = PROJECT_ROOT / "archived"
    if not archived_dir.exists():
        print("   ℹ️  archived 目录不存在")
        return 0
    
    debug_files = [
        "debug_twitter.html",
    ]
    
    # 删除 .DS_Store
    ds_store = archived_dir / ".DS_Store"
    if ds_store.exists():
        ds_store.unlink()
        print(f"   ✅ 删除: archived/.DS_Store")
    
    removed = []
    for filename in debug_files:
        file_path = archived_dir / filename
        if file_path.exists():
            file_path.unlink()
            removed.append(filename)
            print(f"   ✅ 删除: archived/{filename}")
    
    if not removed and not ds_store.exists():
        print("   ℹ️  无 debug 文件需要清理")
    
    return len(removed)


def update_gitignore():
    """更新 .gitignore 以忽略临时文件"""
    print("\n📝 更新 .gitignore...")
    
    gitignore_path = PROJECT_ROOT / ".gitignore"
    
    entries_to_add = [
        "\n# 临时和测试数据",
        "browser_data_debug/",
        "browser_data_test/",
        "temp_xhs/",
        "test_archived/",
        "test_images/",
        "",
        "# Debug 文件",
        "debug_*.py",
        "debug_*.html",
        "",
        "# 临时测试文件（根目录）",
        "/test_*.py",
        "",
        "# 归档目录中的临时文件",
        "archived/.DS_Store",
        "archived/debug_*",
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已有相关配置
        if "临时和测试数据" in content:
            print("   ℹ️  .gitignore 已包含相关配置")
            return False
        
        # 添加新配置
        with open(gitignore_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(entries_to_add))
        
        print("   ✅ 已更新 .gitignore")
        return True
    else:
        print("   ⚠️  .gitignore 不存在")
        return False


def show_summary(stats):
    """显示清理摘要"""
    print("\n" + "=" * 60)
    print("📊 清理摘要")
    print("=" * 60)
    
    total_files = (stats['debug_files'] + stats['test_files'] + 
                   stats['archived_debug'])
    total_dirs = stats['browser_dirs'] + stats['temp_dirs']
    total_size = stats['browser_size'] + stats['temp_size']
    
    print(f"\n✅ 已删除文件: {total_files} 个")
    print(f"✅ 已删除目录: {total_dirs} 个")
    print(f"✅ 释放空间: {total_size:.1f} MB")
    
    if stats['gitignore_updated']:
        print("✅ 已更新 .gitignore")
    
    print("\n💡 项目现在更加整洁和工程化！")
    print("\n建议后续操作:")
    print("  1. 运行 make selftest 确保功能正常")
    print("  2. 提交清理后的代码: git add . && git commit -m 'chore: 清理临时和debug文件'")
    print("=" * 60)


def main():
    """主函数"""
    import sys
    
    print("=" * 60)
    print("🧹 项目清理工具")
    print("=" * 60)
    print()
    print("将清理以下内容:")
    print("  • Debug 文件 (debug_*.py)")
    print("  • 临时测试文件 (根目录的 test_*.py)")
    print("  • 临时浏览器数据 (browser_data_debug, browser_data_test)")
    print("  • 临时目录 (temp_xhs, test_archived, test_images)")
    print("  • 归档目录中的 debug 文件")
    print()
    
    # 支持 --yes 参数自动确认
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv
    
    if not auto_confirm:
        response = input("确认清理? (y/N): ")
        if response.lower() != 'y':
            print("\n❌ 已取消")
            return
    
    print("\n开始清理...\n")
    
    stats = {
        'debug_files': cleanup_debug_files(),
        'test_files': cleanup_test_files(),
        'archived_debug': cleanup_archived_debug(),
    }
    
    browser_count, browser_size = cleanup_browser_data()
    stats['browser_dirs'] = browser_count
    stats['browser_size'] = browser_size
    
    temp_count, temp_size = cleanup_temp_dirs()
    stats['temp_dirs'] = temp_count
    stats['temp_size'] = temp_size
    
    stats['gitignore_updated'] = update_gitignore()
    
    show_summary(stats)


if __name__ == "__main__":
    main()
