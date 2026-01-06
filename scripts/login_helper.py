"""
浏览器登录辅助脚本
用于一次性完成各平台的登录，保存登录态到 browser_data
"""

import sys
from pathlib import Path

try:
    from DrissionPage import ChromiumOptions, ChromiumPage
except ImportError:
    print("错误: 请先安装 DrissionPage")
    print("运行: pip install DrissionPage")
    sys.exit(1)


def login_helper(browser_data_dir: str = "./browser_data"):
    """
    打开浏览器供用户手动登录
    
    Args:
        browser_data_dir: 浏览器数据目录
    """
    # 确保目录存在
    Path(browser_data_dir).mkdir(parents=True, exist_ok=True)
    
    # 配置浏览器
    co = ChromiumOptions()
    co.set_user_data_path(browser_data_dir)
    co.headless(False)  # 必须显示窗口
    
    # 反爬虫配置
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_user_agent(
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    
    print("=" * 60)
    print("🌐 浏览器登录辅助工具")
    print("=" * 60)
    print()
    print("浏览器窗口将打开，请在窗口中完成以下操作：")
    print()
    print("1. 访问需要归档的平台（知乎/小红书/B站等）")
    print("2. 点击登录，完成登录流程")
    print("3. 勾选 '记住我' 或 '自动登录'")
    print("4. 确认登录成功后，关闭浏览器或按 Ctrl+C")
    print()
    print("⚠️  注意：")
    print("   - 登录数据会自动保存到: " + browser_data_dir)
    print("   - 下次归档时会自动使用这些登录态")
    print("   - 如需重新登录，运行 'make reset-browser'")
    print()
    print("=" * 60)
    print()
    
    # 启动浏览器
    page = ChromiumPage(addr_or_opts=co)
    
    # 打开常用平台的登录页
    print("正在打开浏览器...")
    
    # 可以预先打开一些常用平台
    # page.get("https://www.zhihu.com/")
    
    try:
        input("\n按 Enter 键退出程序（登录数据已自动保存）...")
    except KeyboardInterrupt:
        print("\n\n✓ 登录数据已保存，可以开始归档了！")
    finally:
        page.quit()


if __name__ == "__main__":
    # 从命令行参数获取浏览器数据目录
    browser_data_dir = sys.argv[1] if len(sys.argv) > 1 else "./browser_data"
    login_helper(browser_data_dir)
