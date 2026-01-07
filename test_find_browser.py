#!/usr/bin/env python3
"""
测试可用的浏览器
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from DrissionPage import ChromiumOptions, Chromium

def test_browser_paths():
    """测试不同浏览器路径"""
    
    # 路径1: 项目 Chromium
    project_chromium = Path(__file__).parent / "chromium/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    print(f"项目 Chromium: {project_chromium}")
    print(f"  存在: {project_chromium.exists()}")
    
    # 路径2: Playwright Chromium
    playwright_path = Path.home() / "Library/Caches/ms-playwright"
    print(f"\nPlaywright 目录: {playwright_path}")
    print(f"  存在: {playwright_path.exists()}")
    if playwright_path.exists():
        chromium_dirs = sorted(list(playwright_path.glob("chromium-*")), reverse=True)
        print(f"  Chromium 版本: {[d.name for d in chromium_dirs]}")
        for d in chromium_dirs[:2]:  # 只检查前2个
            for arch in ["arm64", ""]:
                suffix = f"-{arch}" if arch else ""
                app_path = d / f"chrome-mac{suffix}/Google Chrome for Testing.app"
                exe_path = app_path / "Contents/MacOS/Google Chrome for Testing"
                if exe_path.exists():
                    print(f"  ✓ 找到: {exe_path}")
                    return str(exe_path)
    
    # 路径3: 系统 Chrome
    system_chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    print(f"\n系统 Chrome: {system_chrome}")
    print(f"  存在: {Path(system_chrome).exists()}")
    if Path(system_chrome).exists():
        return system_chrome
    
    return None

def test_launch(browser_path):
    """测试启动浏览器"""
    if not browser_path:
        print("\n❌ 未找到可用的浏览器")
        return False
    
    print(f"\n测试启动浏览器: {browser_path}")
    
    options = ChromiumOptions()
    options.set_browser_path(browser_path)
    options.set_local_port(9777)
    options.set_user_data_path(str(Path("browser_data_test").absolute()))
    options.set_argument('--no-sandbox')
    options.set_argument('--disable-dev-shm-usage')
    options.set_argument('--headless=new')  # 使用新的 headless 模式
    
    try:
        print("  → 启动浏览器...")
        browser = Chromium(addr_or_opts=options)
        print(f"  ✓ 浏览器启动成功！PID: {browser.process_id if hasattr(browser, 'process_id') else 'N/A'}")
        
        print("  → 创建标签页...")
        tab = browser.new_tab()
        print(f"  ✓ 标签页创建成功")
        
        print("  → 访问测试页面...")
        tab.get("https://www.example.com")
        print(f"  ✓ 页面加载成功: {tab.title}")
        
        tab.close()
        browser.quit()
        print("  ✓ 清理完成")
        return True
        
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("浏览器测试")
    print("=" * 60)
    
    browser_path = test_browser_paths()
    if browser_path:
        test_launch(browser_path)
    else:
        print("\n❌ 未找到任何可用的浏览器")
