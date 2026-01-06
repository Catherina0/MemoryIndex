"""
重置浏览器数据
清空 browser_data 文件夹，作为全新浏览器重新开始
"""

import shutil
import sys
from pathlib import Path


def reset_browser(browser_data_dir: str = "./browser_data", force: bool = False):
    """
    重置浏览器数据
    
    Args:
        browser_data_dir: 浏览器数据目录
        force: 是否强制删除（不询问）
    """
    data_path = Path(browser_data_dir)
    
    if not data_path.exists():
        print(f"✓ 浏览器数据目录不存在，无需重置")
        return
    
    print("=" * 60)
    print("🔄 重置浏览器数据")
    print("=" * 60)
    print()
    print(f"将要删除的目录: {data_path.absolute()}")
    print()
    print("⚠️  警告：这将删除以下数据：")
    print("   - 所有平台的登录态（Cookies）")
    print("   - 浏览器缓存")
    print("   - 浏览器历史记录")
    print("   - 浏览器指纹数据")
    print()
    
    if not force:
        confirm = input("确认删除？(yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("已取消")
            return
    
    try:
        shutil.rmtree(data_path)
        print()
        print("✓ 浏览器数据已重置")
        print("✓ 下次归档时将使用全新的浏览器环境")
        print()
        print("💡 提示: 运行 'make login' 重新登录各平台")
        print()
    except Exception as e:
        print(f"错误: 删除失败 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 从命令行参数获取选项
    force = "--force" in sys.argv or "-f" in sys.argv
    browser_data_dir = "./browser_data"
    
    # 从参数中提取目录路径
    for arg in sys.argv[1:]:
        if not arg.startswith('-'):
            browser_data_dir = arg
            break
    
    reset_browser(browser_data_dir, force)
