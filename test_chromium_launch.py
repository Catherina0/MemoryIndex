#!/usr/bin/env python3
"""测试独立 Chromium 的启动"""

import sys
from pathlib import Path
from DrissionPage import ChromiumOptions, Chromium
import time

def test_chromium():
    print("=" * 60)
    print("测试独立 Chromium 启动")
    print("=" * 60)
    
    # 配置
    options = ChromiumOptions()
    
    # 设置 Chromium 路径
    chromium_path = Path(__file__).parent / "chromium/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    print(f"\n1. Chromium 路径: {chromium_path}")
    print(f"   存在: {chromium_path.exists()}")
    
    if not chromium_path.exists():
        print("❌ Chromium 不存在！")
        return False
    
    options.set_browser_path(str(chromium_path))
    
    # 设置用户数据目录
    user_data = Path(__file__).parent / "browser_data_test"
    user_data.mkdir(exist_ok=True)
    options.set_user_data_path(str(user_data.absolute()))
    print(f"\n2. 用户数据目录: {user_data.absolute()}")
    
    # 基本参数
    options.set_argument('--no-sandbox')
    options.set_argument('--disable-dev-shm-usage')
    options.set_argument('--disable-gpu')
    options.set_argument('--remote-debugging-port=9222')
    
    print("\n3. 尝试启动浏览器...")
    
    try:
        browser = Chromium(addr_or_opts=options)
        print(f"✓ 浏览器启动成功！")
        print(f"   地址: {browser.address}")
        
        # 测试打开页面
        print("\n4. 测试打开页面...")
        tab = browser.latest_tab
        tab.get("https://www.baidu.com")
        time.sleep(2)
        print(f"   标题: {tab.title}")
        
        print("\n5. 等待 5 秒后关闭...")
        time.sleep(5)
        
        browser.quit()
        print("✓ 测试完成！")
        return True
        
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_chromium()
    sys.exit(0 if success else 1)
