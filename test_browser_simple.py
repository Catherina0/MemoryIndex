#!/usr/bin/env python3
"""
简单测试 DrissionPage 浏览器启动
"""
from pathlib import Path
from DrissionPage import ChromiumOptions, Chromium

# 配置
project_chromium = Path(__file__).parent / "chromium/chrome-mac/Chromium.app"
chromium_executable = project_chromium / "Contents/MacOS/Chromium"

print(f"Chromium路径: {chromium_executable}")
print(f"Chromium存在: {chromium_executable.exists()}")

options = ChromiumOptions()
options.set_browser_path(str(chromium_executable))
options.set_local_port(9444)  # 使用不同端口
options.set_user_data_path(str(Path("browser_data_test").absolute()))

# 测试1: 不使用headless
print("\n测试1: 不使用headless模式...")
options.set_argument('--no-sandbox')
options.set_argument('--disable-dev-shm-usage')

try:
    browser = Chromium(addr_or_opts=options)
    print(f"✓ 浏览器启动成功！")
    print(f"  PID: {browser.process_id if hasattr(browser, 'process_id') else 'N/A'}")
    
    # 创建标签页
    tab = browser.new_tab()
    print(f"✓ 标签页创建成功")
    print(f"  Title: {tab.title}")
    
    # 访问页面
    tab.get("https://www.baidu.com")
    print(f"✓ 页面访问成功: {tab.title}")
    
    # 清理
    tab.close()
    browser.quit()
    print(f"✓ 浏览器已关闭")
    
except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()
